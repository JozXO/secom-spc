# LEARN.md: study guide for the SECOM SPC project

This is for Josiah. The goal: you can explain every step in your own words and rewrite the key queries from a blank page, with no AI. An interviewer who opens this repo will ask you to do exactly that, probably on a shared screen.

How to study each query:

1. Read "What it answers" and "How it works".
2. Close the file. Open a blank editor. Write the query from memory using the table and column names below.
3. Run it (`python run_all.py --show`, or open `secom.duckdb` in any DuckDB client). Compare with the real file. Fix the gaps.
4. Say the interview sentence out loud once.

Do not memorise the text of the queries. Memorise the shape: what is the question, which table, which grouping, which filter, which window.

## Read this first: what is yours and what is background

- **Yours (you did it, you can defend it):** loading the data, the rules in `RULES.md`, the SQL, the checks, the charts, the numbers.
- **Background (you read it, you have not done it at work):** how fabs use SPC, FDC and run-to-run control in real life. The section "Background: SPC, FDC and R2R" below is at new-graduate level. Never say you did fab SPC. Say you built an SPC-style analysis on a public semiconductor dataset.
- **The data:** UCI SECOM (McCann and Johnston, donated 2008). 1,567 production runs from a semiconductor manufacturing line, 590 sensor or measurement columns, a pass/fail label from an in-house line test, and a timestamp. The sensors are anonymised (columns 1 to 590, no names, no units, no process step). So you cannot say what a sensor measures. That is a limit to state up front.

## The tables

**`runs`**: one row per production run (1,567 rows).

| column | meaning |
|---|---|
| `run_id` | 1 to 1,567 in time order (checked: timestamps never go backwards) |
| `ts` | when the run was tested, 19 Jul 2008 to 17 Oct 2008 |
| `label_raw` | -1 = pass, 1 = fail (as in the raw file) |
| `result` | 'pass' or 'fail' |
| `is_fail` | 1 if fail, else 0. `avg(is_fail)` is the fail rate |

**`readings`**: one row per run and sensor that has a value (882,579 rows). A missing value has no row, so `count(*)` for a sensor = the runs where it was measured. Columns: `run_id`, `sensor` (1 to 590), `value`.

Tables built by the files in `queries/build/` (run in order by `pipeline.py`):

| table | what it holds |
|---|---|
| `run_windows` | each run with its 100-run `win` (1 to 16) and `in_baseline` (first 300 runs) |
| `usable` | the 415 sensors good enough to chart |
| `limits` | per usable sensor: `centre`, `sigma`, `ucl`, `lcl` from the baseline |
| `flags` | every usable reading with its z-score and `rule1`, `rule2`, `rule5` true/false |
| `zwin` | every usable reading as a z-score inside its own window |
| `separation` | per sensor: `t_raw`, `t_same`, `auc`, ranks |
| `separation_half` | `t_same` computed separately on the first and second half of the runs |
| `capa` | every flagged excursion with whether the next window recovered |

## Words you need

- **Process:** the thing being made. Here, a production run on a semiconductor line.
- **Variation:** no two runs give the same number. SPC separates *normal* variation (always there, small, random) from *unusual* variation (a cause you could find).
- **Control chart:** a time-ordered plot of a measurement with a centre line and limits. A point or pattern outside what the limits allow is a signal to look.
- **Control limits:** calculated from the process's own past data, usually centre line plus or minus 3 sigma. They answer "what does this process normally do?". They are NOT specification limits (what the customer or design needs). A process can be in control and still out of spec, or the reverse.
- **Sigma (standard deviation):** the typical spread. 3 sigma limits catch about 99.7% of points if the data are normal, steady and independent. That is the theory; Q3 shows these data do not behave that way.
- **Individuals chart (I chart):** one value per point, no subgroups. Used here because each run gives one reading per sensor.
- **Moving range (MR):** the absolute difference between a value and the one before it. The average MR divided by 1.128 estimates sigma for an individuals chart. Reason: it measures run-to-run jumps and ignores slow drift, so a slowly drifting process still gets limits that are sensitive to the drift. (1.128 is the standard constant for moving ranges of 2; you can say "a standard constant from SPC tables".)
- **Baseline window:** the early stretch of data used to set the limits. After that, new points are judged against those fixed limits ("monitoring").
- **Zones:** the bands between the centre line and +/-1, +/-2 and +/-3 sigma. Some rules count points in zones.
- **Nelson rules / Western Electric rules:** written patterns that count as signals besides "outside 3 sigma". We use three:
  - Rule 1: one point beyond 3 sigma. Catches a sudden jump or spike.
  - Rule 2: nine points in a row on the same side of the centre line. Catches a small sustained shift. For normal independent data, a given point completes such a run with probability about 2 x (1/2)^9 = 0.4%.
  - Rule 5: two of three points in a row beyond 2 sigma on the same side. Catches a developing shift.
- **Alarm point:** a point that breaks a rule. A long run on one side gives many alarm points in a row.
- **Excursion:** in this project, a sensor-window with 3 or more Rule 1 alarm points (defined in `RULES.md`). (In a fab, "excursion" usually means any event outside normal that needs a response, such as a yield drop or an out-of-limit measurement.)
- **Yield:** passes divided by runs. Fail rate = 1 minus yield.
- **p chart:** a control chart for a proportion (fail rate). Limits = p plus or minus 3 x sqrt(p(1-p)/n), where p is the baseline rate and n the runs in the window. Smaller windows get wider limits.
- **CAPA:** corrective and preventive action, the quality system record of "what went wrong, what was done, did it work". Our table is a simplified imitation using only what the data can show.
- **Welch t statistic:** (mean of group A minus mean of group B) divided by its standard error, without assuming equal spread. Bigger absolute value = a bigger gap compared with the noise.
- **AUC (area under the ROC curve):** the chance that a randomly chosen fail run has a higher reading than a randomly chosen pass run (ties count half). 0.5 = no separation.
- **Same-period comparison:** compare fail and pass runs inside the same window, so slow drift over time does not fake a relationship. Fail runs are not spread evenly over time (more early on), so without this a drifting sensor would look related to failures.
- **Label-shuffle (permutation) test:** shuffle the pass/fail labels inside each window many times, recompute the best |t| each time. That shows how large the best score gets when there is no relationship. It is the honest yardstick when you rank hundreds of sensors, because some will look good by luck.

## Background: SPC, FDC and R2R (new-graduate level, not my experience)

This is what I learned from reading about semiconductor manufacturing, kept simple.

- **SPC (statistical process control):** charts and rules on a measured result or key parameter, usually one number per lot or wafer (for example a film thickness or a line width). Goal: notice when the process moves. This project is SPC-style work.
- **FDC (fault detection and classification):** monitoring of the *equipment sensor signals recorded during a process step* (temperature, pressure, gas flow, power and so on), many signals at once, often several readings per second within a run. Goal: detect that a tool is behaving abnormally and say what kind of fault it looks like. It is usually much more data and more multivariate than SPC.
- **R2R (run-to-run control):** not monitoring but *adjusting*. After each run (or lot) the measured result is used to change the recipe setting for the next run, so the output stays on target as the tool drifts. SPC and FDC raise an alert; R2R acts.
- **One sentence to tell them apart:** SPC watches results, FDC watches tool signals, R2R changes the next recipe.
- SECOM is a mix: many sensor-like columns (FDC-flavoured) with one pass/fail result per run, treated here with SPC tools.

## Step by step

### Loading: `fetch_data.py`, `load_data.py`
- `fetch_data.py` downloads the UCI zip, writes only the three expected file names to `data/raw/`, and checks the shape is 1,567 x 590 with 1,567 labels. It stops if the shape is wrong.
- `load_data.py` reads `secom.data` (space separated, `NaN` for missing) and `secom_labels.data` (label and a quoted timestamp). The timestamp is day/month/year, so the format is given explicitly (`%d/%m/%Y %H:%M:%S`); letting a library guess would swap day and month. It makes the `runs` and `readings` tables. Missing values are dropped from `readings`, not filled in.
- Interview sentence: "I load the raw SECOM files into DuckDB with a loader that checks the row counts, and I parse the day/month/year timestamps explicitly."

### Build 01, `run_windows.sql`
- `1 + (run_id - 1) // 100` gives 1 for runs 1 to 100, 2 for 101 to 200, and so on. `//` is whole-number division.
- `run_id <= 300 AS in_baseline` marks the first 300 runs.
- Why 100 and 300: equal-sized windows have equal weight; three windows give a baseline of 300 points per sensor, which is enough for a mean and a sigma. These were fixed before charting (`RULES.md`).
- Interview sentence: "I split the runs into windows of 100 in time order and used the first three as the baseline."

### Build 02, `usable_sensors.sql`
- `GROUP BY sensor` then `HAVING` keeps sensors that pass four tests: measured in at least 90% of runs, at least 270 of the 300 baseline runs, at least 10 different values, a baseline standard deviation above 0.
- `count(*) FILTER (WHERE w.in_baseline)` counts only the baseline rows. `FILTER` is "aggregate only these rows".
- Result: 415 of 590 sensors. Q2 shows why the other 175 drop out: 116 are constant, 52 are missing in over 10% of runs, 7 have fewer than 10 different values.
- Interview sentence: "Before charting I removed constant, mostly missing and on/off style columns, so every chart is a sensor that actually varies."

### Build 03, `control_limits.sql` (key query: be able to rewrite it)
Line by line:
1. `WITH ordered AS (...)`: for each reading of a usable sensor, `abs(value - lag(value) OVER (PARTITION BY sensor ORDER BY run_id))` is the moving range: the jump from the previous measured value of the same sensor. The first row of a sensor has no previous value, so it is NULL, and `avg()` ignores NULLs.
2. `base`: per sensor, `avg(value) FILTER (WHERE in_baseline)` is the centre line; `avg(moving_range) FILTER (WHERE in_baseline) / 1.128` is sigma. Only baseline rows are used, so later data cannot change the limits.
3. Final `SELECT`: `ucl = centre + 3 * sigma`, `lcl = centre - 3 * sigma`.
- Interview sentence: "Limits come only from the baseline: the centre is the baseline mean and sigma is the average moving range divided by 1.128, so each sensor's limits reflect its own run-to-run behaviour."

### Build 04, `alarm_flags.sql` (key query: be able to rewrite it)
Line by line:
1. `z`: join each reading to its sensor's limits and compute `(value - centre) / sigma`, how many sigmas from the centre.
2. `side`: +1 above the centre, -1 below, 0 exactly on it.
3. `roll`: two named windows over the same sensor in run order. `w9` is the current row plus the 8 before (`ROWS BETWEEN 8 PRECEDING AND CURRENT ROW`), `w3` the current plus 2 before. `min(side)` and `max(side)` over `w9` are equal only if all 9 are on the same side; `count(*)` over `w9` must be 9 so the first 8 rows of a sensor cannot flag. `hi3` and `lo3` count how many of the last 3 are above +2 or below -2 sigma.
4. Final `SELECT`: `rule1 = abs(z) > 3`; `rule2 = n9 = 9 AND min9 = max9 AND min9 <> 0`; `rule5 = (z > 2 AND hi3 >= 2) OR (z < -2 AND lo3 >= 2)`. The `z > 2` part makes sure the current point is itself one of the outliers.
- Missing readings have no row, so "the previous 8 rows" means the previous 8 measured values, not the previous 8 runs. State that if asked.
- Interview sentence: "I wrote the Nelson rules as window functions: one filter for 3 sigma, a 9-row frame whose min and max sign agree for a run on one side, and a 3-row frame counting points beyond 2 sigma."

### Build 05 and 06, `window_zscores.sql`, `separation.sql`
- `zwin`: z-score inside the sensor's own window: `(value - avg(value) OVER ws) / nullif(stddev_samp(value) OVER ws, 0)` where `ws` partitions by sensor and window. `nullif(x, 0)` turns a zero spread into NULL so there is no division by zero.
- `separation`: per sensor, split readings by `is_fail`, then `avg`, `var_samp` and `count` of each group with `FILTER`. Welch t = difference in means / sqrt(var_fail/n_fail + var_pass/n_pass). `t_raw` uses raw values, `t_same` uses the within-window z-scores.
- AUC: `rank()` over the sensor's values, plus `(count of equal values - 1) / 2` so tied values share the middle rank. Then AUC = (sum of fail ranks - n_fail(n_fail+1)/2) / (n_fail x n_pass). This is the Mann-Whitney U statistic divided by the number of fail-pass pairs.
- `rank() OVER (ORDER BY abs(t_same) DESC)` gives rank 1 to the largest absolute t.
- Interview sentence: "I ranked sensors by a Welch t on within-window z-scores so slow drift cannot fake a link to failures, and checked it with AUC and a label-shuffle test."

### Build 07, `separation_halves.sql`
- Same t, computed separately for runs 1 to 783 (half A) and 784 to 1,567 (half B). If a sensor is truly related to failures, it should score similarly in both halves.

### Build 08, `capa_log.sql`
- `hits`: Rule 1 alarm points per sensor per monitoring window. `win_yield`: the fail rate per window.
- Join `hits` to itself one window later (`n.win = h.win + 1`, a `LEFT JOIN` so a missing next window counts as 0 via `coalesce`). `HAVING`-style filter `WHERE h.r1_hits >= 3` keeps flagged excursions.
- `next_window` = 'recovered' if the next window has under 3 Rule 1 points for that sensor, 'persists' if not, 'no next window' for window 16.
- Interview sentence: "My CAPA-style table lists each excursion, whether the same sensor recovered in the next window, and the line's fail rate before and after, as association only."

### The questions in `queries/`
| Query | What it answers | Shape to remember |
|---|---|---|
| Q1 | runs, fails, fail rate per week | `GROUP BY date_trunc('week', ts)` plus a total row with `UNION ALL` |
| Q2 | why sensors drop out | `CASE` first-match-wins over per-sensor counts, then `GROUP BY` the label |
| Q3 | do limits behave as theory says on their own baseline | `avg(rule::INT)` for a rate, `median()` of a ratio |
| Q4 | alarm rate by window | `GROUP BY win`, `count(DISTINCT sensor) FILTER (WHERE rule1)` |
| Q5 | fail rate p chart | one-row CTE for p, cross join it to the windows, `CASE` for the signal |
| Q6 | top 15 sensors by same-period t | `ORDER BY rank_same LIMIT 15` |
| Q7 | does the ranking hold in the second half | two CTEs of ranks, joined on sensor |
| Q8 | which 4 sensors get drawn | `UNION ALL` of two ranked `LIMIT` queries |
| Q9 | CAPA table, top 12 | `ORDER BY r1_hits DESC LIMIT 12` |
| Q10 | CAPA summary | `GROUP BY next_window` |
| Q11 | sensors starting an excursion, by window | `NOT EXISTS` against the previous window, `LAG` for the previous fail rate |

## What the numbers say (every one is in the check table)

1. **The process changed a lot between the baseline and later.** Fail rate was 14.7% in the first 300 runs and then ran at 2 to 6% in windows 5 to 13, 15 and 16, with one rise to 12% in window 14. Nine of the 13 monitoring windows are below the lower limit; none is above the upper limit (Q5).
2. **The limits are tight for these sensors.** On the baseline data they were fitted from, Rule 1 alarms 2.84% of points (theory says about 0.27%), Rule 2 11.1% (theory about 0.4%), Rule 5 2.6% (about 0.2%). Median limit sigma is 0.82 of the plain baseline standard deviation, so many sensors drift or move in steps even in the baseline (Q3). The baseline itself was not a calm period: its fail rate was the highest of the whole data.
3. **Alarm rates rise over time:** Rule 1 alarms about 2 to 4% of points in the baseline windows and 5 to 6% in the last windows (Q4). Most flagged excursions do not recover: of 1,593 sensor-windows with 3 or more Rule 1 points, 1,027 persist into the next window, 464 recover and 102 have no next window (Q10). Many sensors moved to a new level and stayed there.
4. **No sensor separates fail from pass better than chance would.** The best same-period |t| is 3.76 (sensor 60). When pass/fail labels are shuffled inside windows, the best |t| over 415 sensors has a median of 3.38 and a 95th percentile of 4.43. Zero sensors beat the 95th percentile. The correlation between half A and half B scores is 0.14 (Q7). Of the first-half top 10, only sensors 60 and 22 stay near the top with the same sign in the second half (ranks 71 and 45 of 415); the other eight fall to rank 99 or lower and four of them flip sign. That is the most that can be said.
5. **Bursts of sensors changing together:** 116 sensors have an excursion in window 4 (19 to 22 Aug), 56 start one in window 15 (7 to 14 Oct), right after window 14 (4 to 7 Oct), which has a 12% fail rate (Q11). That pattern fits a shared cause, but with anonymised sensors and no process log the data cannot name it.

What I would say about limits: this is a public, anonymised dataset with no process context, so the work shows the method and the habit of checking, not a finding about a real fab.

## The one-sentence answers

- **What did you build?** "An SPC-style analysis of the public SECOM semiconductor dataset in DuckDB SQL and Python: Shewhart individuals charts with limits from an early baseline, Nelson rules written before I looked at results, a yield p chart, a pass/fail sensor ranking, and a CAPA-style table, each result cross-checked by an independent recomputation."
- **What did you find?** "The line's fail rate fell from about 15% in the baseline to mostly 2 to 6% afterwards; most excursions were level shifts that persisted; and no single sensor separated fail from pass better than a label-shuffle test says chance would."
- **Why is that a useful result?** "It shows I check my own ranking against chance before calling a sensor important, and the write-up says plainly that the limits were tight for these sensors."
- **Do you have fab experience?** "No. This is a public dataset and I built it to learn the SPC method properly. I can explain every step and rewrite the queries."
- **SPC vs FDC vs R2R?** "SPC watches results, FDC watches the tool's sensor signals, R2R adjusts the next run's recipe. I did SPC-style work; I know the other two from reading."
- **Why 3 sigma and the moving range?** "3 sigma limits flag about 3 in 1,000 normal points; for single values the moving range gives a sigma that reacts to run-to-run noise."
- **Why shuffle the labels?** "With 415 sensors and 104 fails, some sensor will look good by luck; shuffling shows how good the best one looks when there is no link."

## Practice exercises (answers below; try each from a blank editor first)

Use `secom.duckdb` (build it once with `python run_all.py`).

1. **Monthly fail rate.** For each calendar month, list runs, fails and fail rate (1 decimal). Use only `runs`.
2. **Limits for one sensor.** For sensor 60 only, from `readings` and `run_windows`, produce the baseline centre, sigma (average moving range / 1.128) and the UCL and LCL. Round to 3 decimals. Use `lag`. Do not read the `limits` table; use it afterwards to check yourself.
3. **Count alarms for one sensor.** Using only `readings` and `limits` (not `flags`), count how many readings of sensor 22 after run 300 are more than 3 sigma from the centre. Then compare with `SELECT count(*) FROM flags WHERE sensor = 22 AND NOT in_baseline AND rule1`.
4. **Change a rule.** Rule 2 uses 9 in a row. Write a query on sensor 60 that counts alarm points after run 300 if the rule used 8 in a row. What is the count, and how does it compare with the 9-in-a-row count in `flags`?
5. **By hand, then explain.** (a) Window 16 has 67 runs and the baseline fail rate is 44 fails in 300 runs. Work out its p chart upper and lower limits by hand, and say why they are wider than for a 100-run window. (b) Why is the Rule 1 alarm rate on the baseline 2.84% when theory says 0.27%, and why does that matter for how you read the monitoring alarms?

### Answers

**1.**
```sql
-- E1
SELECT strftime(ts, '%Y-%m') AS month,
       count(*)                       AS runs,
       sum(is_fail)                   AS fails,
       round(100.0 * avg(is_fail), 1) AS fail_pct
FROM runs
GROUP BY 1
ORDER BY 1;
```
Result: 2008-07: 63 runs, 14 fails, 22.2%; 2008-08: 555, 51, 9.2%; 2008-09: 590, 17, 2.9%; 2008-10: 359, 22, 6.1%. Total 1,567 and 104.

**2.**
```sql
-- E2
WITH s AS (
    SELECT r.run_id, r.value,
           abs(r.value - lag(r.value) OVER (ORDER BY r.run_id)) AS mr
    FROM readings r
    WHERE r.sensor = 60
)
SELECT round(avg(value), 3)                AS centre,
       round(avg(mr) / 1.128, 3)           AS sigma,
       round(avg(value) + 3 * avg(mr) / 1.128, 3) AS ucl,
       round(avg(value) - 3 * avg(mr) / 1.128, 3) AS lcl
FROM s
WHERE run_id <= 300;
```
Result: centre 11.647, sigma 10.769, UCL 43.953, LCL -20.659. The `lag` runs over all of the sensor's rows. The `WHERE run_id <= 300` is in the outer query, so only baseline rows go into the averages. Always ask which rows a window function can see before you add a `WHERE`.

**3.**
```sql
-- E3
SELECT count(*) AS alarm_points
FROM readings r
JOIN limits l USING (sensor)
WHERE r.sensor = 22
  AND r.run_id > 300
  AND abs(r.value - l.centre) / l.sigma > 3;
```
Result: 2, the same as the `flags` count.

**4.**
```sql
-- E4
WITH s AS (
    SELECT run_id, CASE WHEN z > 0 THEN 1 WHEN z < 0 THEN -1 ELSE 0 END AS side
    FROM flags
    WHERE sensor = 60
),
r AS (
    SELECT run_id, min(side) OVER w AS mn, max(side) OVER w AS mx, count(*) OVER w AS n
    FROM s
    WINDOW w AS (ORDER BY run_id ROWS BETWEEN 7 PRECEDING AND CURRENT ROW)
)
SELECT count(*) AS alarm_points
FROM r
WHERE n = 8 AND mn = mx AND mn <> 0 AND run_id > 300;
```
Result: 1,072 with 8 in a row, against 1,056 with 9 in a row. A shorter run is easier to reach, so slightly more alarm points. Sensor 60's level fell and stayed below its early centre line, so both counts are large. The frame is `7 PRECEDING` because 7 before plus the current row is 8 rows. The run_id filter goes in the outer query so the first monitoring rows can still look back into the baseline.

**5.**
(a) p = 44 / 300 = 0.1467. Standard error for n = 67: sqrt(0.1467 x 0.8533 / 67) = sqrt(0.001868) = 0.0432. Three times that is 0.1297. Upper limit 0.1467 + 0.1297 = 27.6%; lower limit 0.1467 - 0.1297 = 1.7%. For n = 100 the standard error is 0.0354 and the limits are 25.3% and 4.1%. Fewer runs mean a noisier fail rate, so the limits must be wider before a result counts as a signal.
(b) The limits assume the baseline points are independent and bell-shaped with a stable level. These sensors drift, move in steps and have heavy tails, so far more points fall outside than theory says. A fair reading: alarms in monitoring are only meaningful when they clearly exceed the rate seen on the baseline itself (2.84% for Rule 1), not the 0.27% from theory. That is why Q3 comes before Q4.

## If you are asked "what would you do next"

Honest, small steps: (1) re-fit the baseline in a calmer period or with a robust method, and compare how many alarms change; (2) check the sensors that moved together in windows 4 and 15 against each other (do they move in the same direction at the same run?); (3) for a real fab, get the sensor names, units and process step so a shift can be tied to a tool or recipe. Do not promise anything beyond what the data show.
