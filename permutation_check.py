"""
permutation_check.py
Label-shuffle test for the pass/fail ranking (RULES.md: "label-shuffle test inside windows").

Question: with 415 usable sensors and only 104 fail runs, how big does the best same-period |t|
get when pass/fail has NO relationship to the sensors?

Method: inside each 100-run window, shuffle the pass/fail labels among that window's runs (so each
window keeps its own fail count), recompute every sensor's same-period Welch t, keep the largest |t|.
Repeat 500 times. If the real best |t| is not above the 95th percentile of those maxima, the best
sensor looks no better than what chance would give.

Python + numpy here because shuffling is awkward in SQL; the real t values come from the SQL table.
"""
import numpy as np
import pandas as pd

N_SHUFFLES = 500
SEED = 2008


def welch_t_matrix(z, fail):
    """z: runs x sensors with NaN for missing. fail: boolean array per run. Returns t per sensor."""
    ok = ~np.isnan(z)
    z0 = np.where(ok, z, 0.0)
    f = fail[:, None] & ok
    p = (~fail)[:, None] & ok
    nf, np_ = f.sum(0), p.sum(0)
    mf = (z0 * f).sum(0) / nf
    mp = (z0 * p).sum(0) / np_
    vf = (((z0 - mf) ** 2) * f).sum(0) / (nf - 1)
    vp = (((z0 - mp) ** 2) * p).sum(0) / (np_ - 1)
    return (mf - mp) / np.sqrt(vf / nf + vp / np_)


def run(con):
    df = con.execute("SELECT sensor, run_id, is_fail, win, z_window FROM zwin").fetchdf()
    z = df.pivot(index="run_id", columns="sensor", values="z_window").sort_index()
    meta = df.drop_duplicates("run_id").set_index("run_id").loc[z.index]
    fail = meta["is_fail"].to_numpy().astype(bool)
    win = meta["win"].to_numpy()
    zv = z.to_numpy(dtype=float)

    real_t = welch_t_matrix(zv, fail)
    rng = np.random.default_rng(SEED)
    maxima = np.empty(N_SHUFFLES)
    for i in range(N_SHUFFLES):
        shuffled = fail.copy()
        for w in np.unique(win):
            idx = np.where(win == w)[0]
            shuffled[idx] = rng.permutation(fail[idx])
        maxima[i] = np.nanmax(np.abs(welch_t_matrix(zv, shuffled)))
    threshold = float(np.percentile(maxima, 95))
    return {
        "real_max_abs_t": float(np.nanmax(np.abs(real_t))),
        "null_median_max": float(np.median(maxima)),
        "null_p95_max": threshold,
        "sensors_above_p95": int((np.abs(real_t) > threshold).sum()),
        "sensors": int(zv.shape[1]),
        "shuffles": N_SHUFFLES,
    }


if __name__ == "__main__":
    from pipeline import build
    print(run(build()))
