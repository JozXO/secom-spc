"""
load_data.py
Builds secom.duckdb from the raw SECOM files in data/raw/ (run fetch_data.py first).

Two tables:
  runs      one row per production run (1,567): run_id, ts, result ('pass' or 'fail'), is_fail (0/1)
  readings  one row per run and sensor: run_id, sensor (1..590), value.
            A missing value (NaN in the raw file) is NOT stored, so
            "count of readings for a sensor" = "runs where it was measured".

Label coding in the raw file: -1 = pass, 1 = fail (from secom.names).
Timestamps are day/month/year (dd/mm/yyyy), so they are parsed explicitly.
"""
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

HERE = Path(__file__).parent
RAW = HERE / "data" / "raw"
DB = HERE / "secom.duckdb"


def load(path=DB):
    if not (RAW / "secom.data").exists():
        raise SystemExit("data/raw/secom.data not found. Run: python fetch_data.py")

    values = pd.read_csv(RAW / "secom.data", sep=r"\s+", header=None, na_values=["NaN"])
    labels = pd.read_csv(RAW / "secom_labels.data", sep=r"\s+", header=None,
                         names=["label_raw", "ts"], quotechar='"')
    assert values.shape == (1567, 590) and len(labels) == 1567

    runs = pd.DataFrame({
        "run_id": np.arange(1, len(labels) + 1),
        "ts": pd.to_datetime(labels["ts"], format="%d/%m/%Y %H:%M:%S"),
        "label_raw": labels["label_raw"],
    })

    # long format: one row per run and sensor, missing values dropped
    long = values.copy()
    long.columns = np.arange(1, 591)
    long.insert(0, "run_id", runs["run_id"].values)
    long = long.melt(id_vars="run_id", var_name="sensor", value_name="value").dropna(subset=["value"])
    long["sensor"] = long["sensor"].astype("int32")

    if Path(path).exists():
        Path(path).unlink()
    con = duckdb.connect(str(path))
    con.register("runs_df", runs)
    con.register("long_df", long)
    con.execute("""
        CREATE TABLE runs AS
        SELECT run_id, ts, label_raw,
               CASE WHEN label_raw = 1 THEN 'fail' ELSE 'pass' END AS result,
               CASE WHEN label_raw = 1 THEN 1 ELSE 0 END           AS is_fail
        FROM runs_df ORDER BY run_id
    """)
    con.execute("CREATE TABLE readings AS SELECT run_id, sensor, value FROM long_df ORDER BY sensor, run_id")
    return con


def check_counts(con):
    """Row counts the UCI page promises. Returns True if all match."""
    n_runs = con.execute("SELECT count(*) FROM runs").fetchone()[0]
    n_fail = con.execute("SELECT sum(is_fail) FROM runs").fetchone()[0]
    n_sensors = con.execute("SELECT count(DISTINCT sensor) FROM readings").fetchone()[0]
    ok = (n_runs, n_fail) == (1567, 104)
    print(f"runs={n_runs}, fails={n_fail}, sensors with any reading={n_sensors}")
    return ok


if __name__ == "__main__":
    c = load()
    print("Built", DB, "OK" if check_counts(c) else "COUNTS DO NOT MATCH")
