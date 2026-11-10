"""
check_learn.py
Runs the answer queries in LEARN.md (the sql blocks that start with a '-- E1' ... '-- E4' comment) and
prints their results next to the numbers stated in LEARN.md, so the study guide cannot drift from the data.

    python check_learn.py
"""
import re
import sys
from pathlib import Path

from pipeline import build

HERE = Path(__file__).parent
EXPECTED = {
    "E1": [("2008-07", 63, 14, 22.2), ("2008-08", 555, 51, 9.2), ("2008-09", 590, 17, 2.9), ("2008-10", 359, 22, 6.1)],
    "E2": [(11.647, 10.769, 43.953, -20.659)],
    "E3": [(2,)],
    "E4": [(1072,)],
}


def main():
    text = (HERE / "LEARN.md").read_text(encoding="utf-8")
    blocks = {m.group(1): m.group(0) for m in re.finditer(r"```sql\n-- (E\d)\n(.*?)```", text, re.S)}
    blocks = {k: re.sub(r"^```sql\n|```$", "", v).strip() for k, v in blocks.items()}
    con = build()
    bad = 0
    for k, exp in EXPECTED.items():
        got = con.execute(blocks[k]).fetchall()
        ok = got == exp
        bad += not ok
        print(f"{k}: {'yes' if ok else 'NO'}  stated {exp}  SQL {got}")
    # exercise 3 comparison and exercise 4 comparison, stated in the text
    f3 = con.execute("SELECT count(*) FROM flags WHERE sensor = 22 AND NOT in_baseline AND rule1").fetchone()[0]
    f4 = con.execute("SELECT count(*) FROM flags WHERE sensor = 60 AND NOT in_baseline AND rule2").fetchone()[0]
    print(f"E3 flags count {f3} (stated 2): {'yes' if f3 == 2 else 'NO'}")
    print(f"E4 9-in-a-row count {f4} (stated 1,056): {'yes' if f4 == 1056 else 'NO'}")
    bad += (f3 != 2) + (f4 != 1056)
    # exercise 5 arithmetic
    import math
    p = 44 / 300
    for n, lo_s, hi_s in ((67, 1.7, 27.6), (100, 4.1, 25.3)):
        se = 3 * math.sqrt(p * (1 - p) / n)
        ok = round(100 * (p + se), 1) == hi_s and round(100 * (p - se), 1) == lo_s
        bad += not ok
        print(f"E5 n={n}: limits {100*(p-se):.1f}% to {100*(p+se):.1f}% (stated {lo_s} to {hi_s}): {'yes' if ok else 'NO'}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
