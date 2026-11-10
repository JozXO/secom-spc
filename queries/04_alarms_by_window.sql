-- Q4. How many alarm points per window, across all usable sensors?
-- Windows 1-3 are the baseline (where the limits were fitted); 4 onward is monitoring.
-- "pct" = alarm points as a share of readings in that window.
-- sensors_with_rule1 = how many different sensors had at least one Rule 1 point in the window.

SELECT win,
       min(run_id)                                  AS first_run,
       max(run_id)                                  AS last_run,
       count(*)                                     AS readings,
       round(100.0 * avg(rule1::INT), 2)            AS rule1_pct,
       round(100.0 * avg(rule2::INT), 2)            AS rule2_pct,
       round(100.0 * avg(rule5::INT), 2)            AS rule5_pct,
       count(DISTINCT sensor) FILTER (WHERE rule1)  AS sensors_with_rule1
FROM flags
GROUP BY win
ORDER BY win;
