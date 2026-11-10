"""
run_all.py
Builds secom.duckdb, runs every query, and prints a check table:
independent recomputation | SQL result | match yes/no.

    python run_all.py            # check table only
    python run_all.py --show     # also print the result of every query

"Independent" means: recomputed from the raw files with plain pandas / numpy / Python loops, with no
DuckDB and none of the SQL logic. The SQL is reported as it is. If a check says NO, the script exits
with an error. The label-shuffle test (permutation_check.py) uses a random seed and has no second
implementation, so its numbers are printed separately and marked as not cross-checked.
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

import permutation_check
from pipeline import build, run

HERE = Path(__file__).parent
RAW = HERE / "data" / "raw"
N_RUNS = 1567
warnings.filterwarnings('ignore', category=RuntimeWarning)  # all-NaN columns in the independent pass


# ---------------------------------------------------------------- independent recomputation
def independent():
    V = pd.read_csv(RAW / "secom.data", sep=r"\s+", header=None, na_values=["NaN"]).to_numpy(float)
    lab = pd.read_csv(RAW / "secom_labels.data", sep=r"\s+", header=None, names=["label", "ts"], quotechar='"')
    ts = pd.to_datetime(lab["ts"], format="%d/%m/%Y %H:%M:%S")
    fail = (lab["label"].to_numpy() == 1)
    idx = np.arange(N_RUNS)
    win = 1 + idx // 100
    base = idx < 300
    ok = ~np.isnan(V)

    n_meas = ok.sum(0)
    n_dist = np.array([len(np.unique(V[ok[:, j], j])) for j in range(V.shape[1])])
    n_base = ok[base].sum(0)
    with np.errstate(all="ignore"):
        sd_base = np.nanstd(V[base], axis=0, ddof=1)
    usable = (n_meas >= 0.9 * N_RUNS) & (n_base >= 270) & (n_dist >= 10) & (sd_base > 0)

    cat = {}
    for j in range(V.shape[1]):
        if n_dist[j] == 1:
            c = "1 constant (one value only)"
        elif n_meas[j] < 0.9 * N_RUNS:
            c = "2 measured in under 90% of runs"
        elif n_dist[j] < 10:
            c = "3 fewer than 10 different values"
        elif usable[j]:
            c = "5 usable"
        else:
            c = "4 other (too little baseline data)"
        cat[c] = cat.get(c, 0) + 1

    out = {"V": V, "ts": ts, "fail": fail, "win": win, "ok": ok, "cat": cat, "n_missing_pct": 100 * (~ok).mean()}
    sensors = [j for j in range(V.shape[1]) if usable[j]]
    lim, alarms = {}, {}
    for j in sensors:
        pos = np.where(ok[:, j])[0]
        v = V[pos, j]
        b = v[pos < 300]
        centre = b.mean()
        sigma = np.abs(np.diff(b)).mean() / 1.128
        z = (v - centre) / sigma
        r1 = np.abs(z) > 3
        r2 = np.zeros(len(z), bool)
        r5 = np.zeros(len(z), bool)
        streak, last = 0, 0
        for i, zi in enumerate(z):
            side = int(zi > 0) - int(zi < 0)
            streak = (streak + 1) if (side != 0 and side == last) else (1 if side != 0 else 0)
            last = side
            r2[i] = streak >= 9
            lo = max(0, i - 2)
            if zi > 2 and (z[lo:i + 1] > 2).sum() >= 2:
                r5[i] = True
            if zi < -2 and (z[lo:i + 1] < -2).sum() >= 2:
                r5[i] = True
        lim[j + 1] = (centre, sigma)
        alarms[j + 1] = dict(pos=pos, r1=r1, r2=r2, r5=r5)
    out["lim"], out["alarms"] = lim, alarms

    # same-period z-scores (inside each 100-run window), matrix runs x sensors
    Z = np.full(V.shape, np.nan)
    for w in np.unique(win):
        rows = win == w
        blk = V[rows]
        m = np.nanmean(blk, 0)
        s = np.nanstd(blk, 0, ddof=1)
        with np.errstate(all="ignore"):
            zz = (blk - m) / s
        # a window where the sensor never changes has no spread; test max == min, because the std of
        # identical floats can come out as 1e-16 instead of exactly 0
        zz[:, np.nanmax(blk, 0) == np.nanmin(blk, 0)] = np.nan
        Z[rows] = zz
    cols = list(sensors)
    ids = [j + 1 for j in sensors]   # sensor numbers as used in SQL (1 to 590)
    out["cols"] = cols

    def welch(M, f):
        o = ~np.isnan(M)
        M0 = np.where(o, M, 0.0)
        F, P = f[:, None] & o, (~f)[:, None] & o
        nf, npp = F.sum(0), P.sum(0)
        mf, mp = (M0 * F).sum(0) / nf, (M0 * P).sum(0) / npp
        vf = (((M0 - mf) ** 2) * F).sum(0) / (nf - 1)
        vp = (((M0 - mp) ** 2) * P).sum(0) / (npp - 1)
        return (mf - mp) / np.sqrt(vf / nf + vp / npp)

    Vu, Zu = V[:, cols], Z[:, cols]
    out["t_raw"] = dict(zip(ids, welch(Vu, fail)))
    out["t_same"] = dict(zip(ids, welch(Zu, fail)))
    ranks = pd.DataFrame(Vu).rank(method="average").to_numpy()
    okU = ~np.isnan(Vu)
    nf = (fail[:, None] & okU).sum(0)
    npp = ((~fail)[:, None] & okU).sum(0)
    rsum = np.where(fail[:, None] & okU, ranks, 0).sum(0)
    out["auc"] = dict(zip(ids, (rsum - nf * (nf + 1) / 2) / (nf * npp)))
    half = idx < 783
    ta, tb = welch(Zu[half], fail[half]), welch(Zu[~half], fail[~half])
    out["half_a"], out["half_b"] = dict(zip(ids, ta)), dict(zip(ids, tb))
    out["half_corr"] = float(np.corrcoef(ta, tb)[0, 1])
    return out


def run_checks():
    con = build()
    q = {p: run(con, p) for p in ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11"]}
    ind = independent()
    perm = permutation_check.run(con)
    rows = []

    def add(query, what, ref, sql, nd=None):
        match = (round(ref, nd) == sql) if nd is not None and isinstance(ref, float) else (ref == sql)
        rows.append((query, what, ref, sql, "yes" if match else "NO"))

    fail, ts, win, V, ok = ind["fail"], ind["ts"], ind["win"], ind["V"], ind["ok"]
    # ---- Q1
    q1 = {r["week_start"]: r for r in q["01"]}
    add("Q1", "Runs", N_RUNS, q1["ALL RUNS"]["runs"])
    add("Q1", "Fail runs", int(fail.sum()), q1["ALL RUNS"]["fails"])
    add("Q1", "Fail rate (%)", float(100 * fail.mean()), q1["ALL RUNS"]["fail_pct"], 1)
    wk = pd.DataFrame({"wk": ts.dt.to_period("W-SUN").dt.start_time.dt.strftime("%Y-%m-%d"), "f": fail})
    g = wk.groupby("wk")["f"].agg(["count", "sum"])
    same = sum(q1[k]["runs"] == int(r["count"]) and q1[k]["fails"] == int(r["sum"]) for k, r in g.iterrows())
    add("Q1", "Weeks with identical runs and fails", f"{len(g)} of {len(g)}", f"{same} of {len(g)}")
    # ---- Q2
    add("Q2", "Share of all sensor cells with no value (%), vs total readings", round(float(ind["n_missing_pct"]), 2),
        round(100.0 * (1 - con.execute("SELECT count(*) FROM readings").fetchone()[0] / (N_RUNS * 590)), 2))
    q2 = {r["category"]: r["sensors"] for r in q["02"]}
    for c in ["1 constant (one value only)", "2 measured in under 90% of runs",
              "3 fewer than 10 different values", "4 other (too little baseline data)", "5 usable"]:
        add("Q2", f"Sensors: {c[2:]}", ind["cat"].get(c, 0), q2.get(c, 0))
    # ---- independent alarm tallies
    al = ind["alarms"]
    base_n = sum((a["pos"] < 300).sum() for a in al.values())
    tot = {k: sum(int((a[k] & (a["pos"] < 300)).sum()) for a in al.values()) for k in ("r1", "r2", "r5")}
    q3 = q["03"][0]
    add("Q3", "Usable sensors", len(al), q3["sensors"])
    add("Q3", "Baseline readings", int(base_n), q3["baseline_readings"])
    for k, name in (("r1", "rule1_pct"), ("r2", "rule2_pct"), ("r5", "rule5_pct")):
        add("Q3", f"Baseline alarm rate, {name[:5]} (%)", float(100 * tot[k] / base_n), q3[name], 2)
    add("Q3", "Sensors with no Rule 1 point in baseline",
        sum(int((a["r1"] & (a["pos"] < 300)).sum()) == 0 for a in al.values()), q3["sensors_with_no_rule1_in_baseline"])
    ratio = [ind["lim"][s][1] / np.std(a_v, ddof=1) for s, a_v in
             ((s, V[:300, s - 1][ok[:300, s - 1]]) for s in al)]
    add("Q3", "Median sigma ratio (limit sigma / baseline SD)", float(np.median(ratio)), q3["median_sigma_ratio"], 2)
    # ---- Q4: every window, all three rules and sensors with Rule 1
    q4 = {r["win"]: r for r in q["04"]}
    good = 0
    for w in range(1, 17):
        rd = sum(int(((win[a["pos"]] == w)).sum()) for a in al.values())
        ok_w = (round(100 * sum(int((a["r1"] & (win[a["pos"]] == w)).sum()) for a in al.values()) / rd, 2) == q4[w]["rule1_pct"]
                and round(100 * sum(int((a["r2"] & (win[a["pos"]] == w)).sum()) for a in al.values()) / rd, 2) == q4[w]["rule2_pct"]
                and round(100 * sum(int((a["r5"] & (win[a["pos"]] == w)).sum()) for a in al.values()) / rd, 2) == q4[w]["rule5_pct"]
                and sum(bool((a["r1"] & (win[a["pos"]] == w)).any()) for a in al.values()) == q4[w]["sensors_with_rule1"])
        good += ok_w
    add("Q4", "Windows where Rule 1, 2, 5 % and sensors-with-Rule-1 all match", "16 of 16", f"{good} of 16")
    # ---- Q5
    q5 = {r["win"]: r for r in q["05"]}
    p = fail[:300].mean()
    add("Q5", "Baseline fail rate (%)", float(100 * p), q5[1]["centre_pct"], 1)
    sig, good = [], 0
    for w in range(1, 17):
        m = win == w
        n, f = int(m.sum()), int(fail[m].sum())
        hi, lo = p + 3 * np.sqrt(p * (1 - p) / n), max(0, p - 3 * np.sqrt(p * (1 - p) / n))
        s = "above UCL" if f / n > hi else "below LCL" if f / n < lo else "in limits"
        good += (q5[w]["fails"] == f and q5[w]["runs"] == n and q5[w]["signal"] == s)
        sig.append(s)
    add("Q5", "Windows where runs, fails and the chart signal all match", "16 of 16", f"{good} of 16")
    add("Q5", "Windows below the lower limit", sig.count("below LCL"), sum(r["signal"] == "below LCL" for r in q["05"]))
    add("Q5", "Windows above the upper limit", sig.count("above UCL"), sum(r["signal"] == "above UCL" for r in q["05"]))
    # ---- Q6
    ts_same = ind["t_same"]
    order = sorted(ts_same, key=lambda s: -abs(ts_same[s]))
    add("Q6", "Top 5 sensors by same-period |t|", str(order[:5]), str([r["sensor"] for r in q["06"][:5]]))
    for r in q["06"][:3]:
        s = r["sensor"]
        add("Q6", f"Sensor {s}: t_same", float(ind["t_same"][s]), r["t_same"], 2)
        add("Q6", f"Sensor {s}: t_raw", float(ind["t_raw"][s]), r["t_raw"], 2)
        add("Q6", f"Sensor {s}: AUC", float(ind["auc"][s]), r["auc"], 3)
    maxdiff = con.execute("SELECT sensor, t_same, t_raw, auc FROM separation").fetchall()
    worst = max(max(abs(a - ind["t_same"][s]), abs(b - ind["t_raw"][s]), abs(c - ind["auc"][s])) for s, a, b, c in maxdiff)
    add("Q6", "All 415 sensors: largest difference in t_same, t_raw, AUC (under 1e-8)", "< 1e-8", "< 1e-8" if worst < 1e-8 else f"{worst:.2e}")
    # ---- Q7
    top_a = sorted(ind["half_a"], key=lambda s: -abs(ind["half_a"][s]))[:10]
    add("Q7", "Top 10 sensors in first half", str(top_a), str([r["sensor"] for r in q["07"]]))
    sql_corr = con.execute("SELECT corr(a.t_same, b.t_same) FROM separation_half a JOIN separation_half b USING (sensor) "
                           "WHERE a.half = 'A' AND b.half = 'B'").fetchone()[0]
    add("Q7", "Correlation of t between the two halves, all sensors", float(ind["half_corr"]), round(sql_corr, 6), 6)
    # ---- Q8
    quiet = min(al, key=lambda s: (sum(int((a["r1"] | a["r2"] | a["r5"])[a["pos"] >= 300].sum()) for a in [al[s]]), s))
    add("Q8", "Charted sensors", str(order[:3] + [quiet]), str([r["sensor"] for r in q["08"]]))
    # ---- Q9 to Q11: CAPA log from independent Rule 1 counts
    hits = {}
    for s, a in al.items():
        for w in range(4, 17):
            n = int((a["r1"] & (win[a["pos"]] == w)).sum())
            if n:
                hits[(s, w)] = n
    exc = {k: v for k, v in hits.items() if v >= 3}
    top20 = set(sorted(ts_same, key=lambda s: -abs(ts_same[s]))[:20])
    cats = {"recovered": [0, 0], "persists": [0, 0], "no next window": [0, 0]}
    onsets = {w: 0 for w in range(4, 17)}
    for (s, w), v in exc.items():
        nxt = "no next window" if w == 16 else ("recovered" if hits.get((s, w + 1), 0) < 3 else "persists")
        cats[nxt][0] += 1
        cats[nxt][1] += s in top20
        if (s, w - 1) not in exc:
            onsets[w] += 1
    q10 = {r["next_window"]: r for r in q["10"]}
    add("Q10", "Flagged excursions (sensor-windows with 3+ Rule 1 points)", len(exc), sum(r["excursions"] for r in q["10"]))
    for k, (n, t) in cats.items():
        add("Q10", f"Excursions: {k}", n, q10.get(k, {}).get("excursions", 0))
        add("Q10", f"  of which sensor in top 20: {k}", int(t), q10.get(k, {}).get("in_top20", 0))
    q9 = q["09"]
    exp9 = sorted(exc.items(), key=lambda kv: (-kv[1], kv[0][0], kv[0][1]))[:12]
    add("Q9", "Top 12 excursions (sensor, window, Rule 1 points)", str([(s, w, v) for (s, w), v in exp9]),
        str([(r["sensor"], r["win"], r["r1_hits"]) for r in q9]))
    q11 = {r["win"]: r["sensors_starting_excursion"] for r in q["11"]}
    add("Q11", "Sensors starting an excursion, windows 4 to 16", str(list(onsets.values())), str([q11[w] for w in range(4, 17)]))
    return rows, q, perm


def fmt(v):
    if isinstance(v, float):
        return f"{v:,.4f}".rstrip("0").rstrip(".") if abs(v) < 1000 else f"{v:,.1f}"
    if isinstance(v, int):
        return f"{v:,}"
    return str(v)


def main():
    show = "--show" in sys.argv
    rows, q, perm = run_checks()
    if show:
        for p, r in q.items():
            print(f"\n--- query {p} ---")
            for x in r:
                print(x)
    head = ("Query", "Check", "Independent", "SQL result", "Match")
    body = [(a, b, fmt(c), fmt(d), e) for a, b, c, d, e in rows]
    w = [max(len(h), *(len(r[i]) for r in body)) for i, h in enumerate(head)]
    line = lambda r: "| " + " | ".join(str(x).ljust(w[i]) for i, x in enumerate(r)) + " |"
    table = [line(head), "|" + "|".join("-" * (x + 2) for x in w) + "|"] + [line(r) for r in body]
    print("\n".join(table))
    (HERE / "check_table.md").write_text("\n".join(table) + "\n", encoding="utf-8")
    n_ok = sum(r[4] == "yes" for r in rows)
    print(f"\n{n_ok} of {len(rows)} checks match.")
    print("\nLabel-shuffle test (not cross-checked, random seed 2008, "
          f"{perm['shuffles']} shuffles inside windows):")
    print(f"  best real same-period |t| = {perm['real_max_abs_t']:.2f}")
    print(f"  best |t| when labels are shuffled: median {perm['null_median_max']:.2f}, 95th percentile {perm['null_p95_max']:.2f}")
    print(f"  sensors above the 95th percentile: {perm['sensors_above_p95']} of {perm['sensors']}")
    if n_ok != len(rows):
        sys.exit("Some checks do not match. See the NO rows.")


if __name__ == "__main__":
    main()
