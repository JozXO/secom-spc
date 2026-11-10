# Rules fixed before any chart or ranking was produced

This file was committed before any control chart, alarm count or sensor ranking was calculated, so the rules were not tuned to the results. Disclosure: while loading the data I did look at the number of runs, the date range, the overall fail count and the fail rate per calendar week (the first week fails 3 of 13 runs, the last weeks 1 to 8 of about 100). The window length and baseline length below were chosen after seeing that, but before any sensor was charted.

## Data conventions
- Runs are in time order (`run_id` 1 to 1,567, checked: timestamps never go backwards).
- Raw label -1 = pass, 1 = fail (from `secom.names`).
- A missing sensor value is left out. Rules run over the measured values of that sensor in time order.

## Windows
- A **window** is 100 consecutive runs (window 1 = runs 1 to 100 ... window 16 = runs 1,501 to 1,567, which has 67 runs).
- **Baseline** = the first 300 runs (windows 1 to 3). Everything after is **monitoring**. Control limits are calculated from the baseline only.

## Which sensors are charted at all ("usable")
A sensor is usable if all of these hold:
1. measured in at least 90% of all runs;
2. measured in at least 270 of the 300 baseline runs;
3. at least 10 different values (this drops on/off and status-style columns);
4. baseline standard deviation above 0.

## Control limits (Shewhart individuals chart, "I chart")
- Centre line = mean of the baseline values.
- Sigma estimate = (average absolute difference between consecutive baseline values) / 1.128. This is the standard moving-range estimate for individual values.
- UCL and LCL = centre line +/- 3 sigma. Zone limits at +/- 1 and +/- 2 sigma.
- No baseline point is removed, even if it looks like an outlier or a failed run.

## Alarm rules (Nelson rules 1, 2 and 5)
A point is an alarm point if it breaks any of these:
- **Rule 1**: the point is more than 3 sigma from the centre line.
- **Rule 2**: this point completes 9 or more values in a row on the same side of the centre line.
- **Rule 5**: this point and at least 1 of the 2 before it are more than 2 sigma from the centre line, all on the same side.

## Yield
- Yield by window = passes / runs. Fail rate = 1 - yield.
- p chart for fail rate: centre = baseline fail rate, limits = centre +/- 3 sqrt(p(1-p)/n) with n = runs in that window.

## Ranking sensors by pass/fail separation
- Method 1: Welch t statistic (difference in means divided by its standard error), fail vs pass, all runs.
- Method 2: same-period version: each value is first converted to a z-score inside its own 100-run window (value minus window mean, divided by window standard deviation), then Welch t on those z-scores. This removes slow drift, because failures are not spread evenly over time.
- Method 3: area under the ROC curve (AUC) from ranks, as a check that does not depend on a few extreme values.
- Only usable sensors are ranked. The ranking is a list of candidates to look at, not proof of cause: with several hundred sensors, some will look good by chance. Two checks are reported: the ranking in the first half of the runs against the second half, and a label-shuffle test inside windows.

## Charted sensors
Four sensors are drawn: the 3 usable sensors with the highest same-period |t|, and the usable sensor with the fewest alarm points in monitoring (a well-behaved comparison). Nothing else is drawn first and then filtered.

## CAPA-style table (corrective and preventive action log, simplified)
- A **flagged excursion** = one sensor in one monitoring window with at least 3 Rule 1 alarm points.
- **Suspected sensor** = the flagged sensor, plus whether it is in the top 20 by same-period |t|.
- **Recovered?** = in the next window the same sensor has fewer than 3 Rule 1 alarm points. Also shown: the fail rate in the flagged window and in the next window.
- This table records association only. It cannot say a sensor caused a failure.
