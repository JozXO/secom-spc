"""
pipeline.py
Shared helpers: build secom.duckdb (load + the SQL files in queries/build/) and run a query file.
"""
from pathlib import Path

from load_data import check_counts, load

HERE = Path(__file__).parent
BUILD = HERE / "queries" / "build"
QUERIES = HERE / "queries"


def build():
    """Load the raw data, then create every table in queries/build/ in file order."""
    con = load()
    if not check_counts(con):
        raise SystemExit("Row counts do not match the UCI description. Stopping.")
    for path in sorted(BUILD.glob("*.sql")):
        con.execute(path.read_text(encoding="utf-8"))
    return con


def run(con, prefix):
    """Run the query file that starts with prefix (e.g. '03'). Returns a list of dict rows."""
    path = next(QUERIES.glob(f"{prefix}_*.sql"))
    cur = con.execute(path.read_text(encoding="utf-8"))
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]
