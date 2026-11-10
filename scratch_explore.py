import pandas as pd
from pipeline import build, run
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
con = build()
for p in ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10"]:
    print("\n--- Q" + p)
    print(pd.DataFrame(run(con, p)).to_string(index=False))
print(con.execute("select corr(a.t_same,b.t_same) from separation_half a join separation_half b using(sensor) where a.half='A' and b.half='B'").fetchall())
