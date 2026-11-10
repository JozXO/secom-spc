-- Q5. Fail rate by 100-run window with p-chart limits from the baseline (windows 1-3).
--   p      = baseline fail rate (fails / runs over the first 300 runs)
--   limits = p +/- 3 * sqrt(p * (1 - p) / n), n = runs in that window; the lower limit cannot go below 0.
-- A window above the upper limit is worse than the baseline allows; below the lower limit is better.

WITH base AS (
    SELECT sum(is_fail) * 1.0 / count(*) AS p
    FROM run_windows
    WHERE in_baseline
),
w AS (
    SELECT win,
           min(ts)::DATE      AS first_day,
           max(ts)::DATE      AS last_day,
           count(*)           AS runs,
           sum(is_fail)       AS fails,
           bool_or(in_baseline) AS in_baseline
    FROM run_windows
    GROUP BY win
)
SELECT win, first_day, last_day, runs, fails,
       round(100.0 * fails / runs, 1)                                              AS fail_pct,
       round(100.0 * p, 1)                                                         AS centre_pct,
       round(100.0 * (p + 3 * sqrt(p * (1 - p) / runs)), 1)                        AS ucl_pct,
       round(100.0 * greatest(0, p - 3 * sqrt(p * (1 - p) / runs)), 1)             AS lcl_pct,
       CASE WHEN fails * 1.0 / runs > p + 3 * sqrt(p * (1 - p) / runs) THEN 'above UCL'
            WHEN fails * 1.0 / runs < p - 3 * sqrt(p * (1 - p) / runs) THEN 'below LCL'
            ELSE 'in limits' END                                                   AS signal
FROM w, base
ORDER BY win;
