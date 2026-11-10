"""
make_charts.py
Draws the charts in charts/ from the tables built by the SQL files. Nothing is calculated here that the
SQL does not already hold (limits, alarm flags, t values); matplotlib only draws.

    python make_charts.py
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import permutation_check
from pipeline import build, run

OUT = Path(__file__).parent / "charts"
BLUE, ORANGE, RED, GREY = "#2b6cb0", "#d9730d", "#c0392b", "#6b7280"


def sensor_chart(con, sensor, why, path):
    lim = con.execute("SELECT centre, sigma FROM limits WHERE sensor = ?", [sensor]).fetchone()
    centre, sigma = lim
    rows = con.execute(
        "SELECT f.run_id, f.value, f.rule1, f.rule2, f.rule5, w.is_fail "
        "FROM flags f JOIN run_windows w USING (run_id) WHERE f.sensor = ? ORDER BY f.run_id", [sensor]
    ).fetchall()
    x = np.array([r[0] for r in rows])
    y = np.array([r[1] for r in rows])
    alarm = np.array([bool(r[2] or r[3] or r[4]) for r in rows])
    fail_x = np.array([r[0] for r in rows if r[5] == 1])

    lo = min(centre - 3.5 * sigma, np.percentile(y, 0.5))
    hi = max(centre + 3.5 * sigma, np.percentile(y, 99.5))
    pad = 0.05 * (hi - lo)
    lo, hi = lo - pad, hi + pad
    off = int(((y < lo) | (y > hi)).sum())

    fig, ax = plt.subplots(figsize=(11, 4.2))
    ax.axvspan(0, 300, color="#e5e7eb", alpha=0.6, label="baseline (runs 1-300)")
    ax.plot(x, y, color=BLUE, lw=0.5, alpha=0.5)
    ax.scatter(x[~alarm], y[~alarm], s=5, color=BLUE, label="no alarm")
    ax.scatter(x[alarm], y[alarm], s=7, color=ORANGE, label="alarm (rule 1, 2 or 5)")
    ax.axhline(centre, color="black", lw=1)
    for k, ls in ((1, ":"), (2, "--"), (3, "-")):
        for s in (k, -k):
            ax.axhline(centre + s * sigma, color=GREY, lw=0.8, ls=ls)
    ax.set_ylim(lo, hi)
    ax.set_xlim(0, 1570)
    ax.plot(fail_x, np.full(len(fail_x), lo + 0.015 * (hi - lo)), "|", color=RED, ms=9, label="fail run")
    ax.set_xlabel("run number (time order, 19 Jul to 17 Oct 2008)")
    ax.set_ylabel(f"sensor {sensor} value")
    sub = f" ({off} point(s) off-scale)" if off else ""
    ax.set_title(f"Sensor {sensor}: individuals chart, limits from runs 1-300. Picked as: {why}{sub}", fontsize=10)
    ax.legend(loc="upper left", fontsize=8, ncol=4, frameon=False)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def yield_chart(con, path):
    rows = run(con, "05")
    win = [r["win"] for r in rows]
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.axvspan(0.5, 3.5, color="#e5e7eb", alpha=0.6, label="baseline (windows 1-3)")
    ax.plot(win, [r["fail_pct"] for r in rows], "o-", color=BLUE, label="fail rate")
    ax.step(win, [r["ucl_pct"] for r in rows], where="mid", color=GREY, label="UCL / LCL")
    ax.step(win, [r["lcl_pct"] for r in rows], where="mid", color=GREY)
    ax.axhline(rows[0]["centre_pct"], color="black", lw=1, label="baseline fail rate")
    for r in rows:
        if r["signal"] != "in limits":
            ax.plot(r["win"], r["fail_pct"], "o", color=ORANGE, ms=9, mfc="none", mew=2)
    ax.set_xticks(win)
    ax.set_xlabel("window (100 runs each, last has 67)")
    ax.set_ylabel("fail rate (%)")
    ax.set_title("Fail rate by window, p chart with limits from windows 1-3 (orange ring = outside limits)", fontsize=10)
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def separation_chart(con, perm, path):
    rows = run(con, "06")
    fig, ax = plt.subplots(figsize=(9, 4.2))
    labels = [f"{r['sensor']}" for r in rows]
    vals = [abs(r["t_same"]) for r in rows]
    ax.bar(labels, vals, color=BLUE)
    ax.axhline(perm["null_median_max"], color=GREY, ls="--",
               label=f"median of best |t| when labels are shuffled ({perm['null_median_max']:.2f})")
    ax.axhline(perm["null_p95_max"], color=RED,
               label=f"95th percentile of best |t| when labels are shuffled ({perm['null_p95_max']:.2f})")
    ax.set_xlabel("sensor number (ranked 1 to 15 by same-period |t|)")
    ax.set_ylabel("|t| fail vs pass (same-period)")
    ax.set_title("Top 15 sensors against what chance alone produces", fontsize=10)
    ax.legend(frameon=False, fontsize=8, loc="lower left")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def onset_chart(con, path):
    rows = run(con, "11")
    win = [r["win"] for r in rows]
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.bar(win, [r["sensors_starting_excursion"] for r in rows], color=BLUE)
    ax.set_xlabel("window")
    ax.set_ylabel("sensors starting an excursion")
    ax.set_xticks(win)
    ax2 = ax.twinx()
    ax2.plot(win, [r["fail_pct"] for r in rows], "o-", color=RED)
    ax2.set_ylabel("fail rate in window (%)", color=RED)
    ax.set_title("Sensors starting an excursion (bars) and window fail rate (line)", fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def main():
    OUT.mkdir(exist_ok=True)
    con = build()
    perm = permutation_check.run(con)
    yield_chart(con, OUT / "yield_p_chart.png")
    separation_chart(con, perm, OUT / "separation_vs_chance.png")
    onset_chart(con, OUT / "excursion_onsets.png")
    for r in run(con, "08"):
        sensor_chart(con, r["sensor"], r["why"], OUT / f"sensor_{r['sensor']}_chart.png")
    print("Charts written to", OUT)


if __name__ == "__main__":
    main()
