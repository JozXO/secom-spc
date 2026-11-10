-- Q1. How many runs, how many failed, and how does the fail rate move week by week?
-- result: 'fail' means the in-house line test failed (label 1 in the raw file).
-- Weeks have very different numbers of runs, so read the runs column next to fail_pct.

SELECT 'ALL RUNS'                              AS week_start,
       count(*)                                AS runs,
       sum(is_fail)                            AS fails,
       round(100.0 * avg(is_fail), 1)          AS fail_pct,
       round(100.0 * (1 - avg(is_fail)), 1)    AS yield_pct
FROM runs

UNION ALL

SELECT strftime(date_trunc('week', ts), '%Y-%m-%d'),
       count(*),
       sum(is_fail),
       round(100.0 * avg(is_fail), 1),
       round(100.0 * (1 - avg(is_fail)), 1)
FROM runs
GROUP BY date_trunc('week', ts)

ORDER BY week_start;   -- 'ALL RUNS' sorts after the dates, which is fine for a short table
