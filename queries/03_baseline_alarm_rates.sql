-- Q3. Do the limits behave as theory says on the baseline data they were built from?
-- If a sensor were stable, normally distributed and independent from run to run, the alarm rates
-- on baseline data would be about: Rule 1 0.27%, Rule 2 0.4%, Rule 5 0.2%.
-- Anything far above that means the limits are too tight for how the sensor really moves.
-- sigma_ratio = limit sigma (from moving ranges) divided by the plain baseline standard deviation.
-- Below 1 means run-to-run jumps are smaller than the spread over the whole baseline, i.e. the sensor drifts.

WITH base AS (
    SELECT f.sensor,
           count(*)               AS n,
           sum(rule1::INT)        AS r1,
           sum(rule2::INT)        AS r2,
           sum(rule5::INT)        AS r5,
           stddev_samp(value)     AS sd
    FROM flags f
    WHERE in_baseline
    GROUP BY f.sensor
)
SELECT count(*)                                        AS sensors,
       sum(n)                                          AS baseline_readings,
       round(100.0 * sum(r1) / sum(n), 2)              AS rule1_pct,
       round(100.0 * sum(r2) / sum(n), 2)              AS rule2_pct,
       round(100.0 * sum(r5) / sum(n), 2)              AS rule5_pct,
       count(*) FILTER (WHERE r1 = 0)                  AS sensors_with_no_rule1_in_baseline,
       round(median(l.sigma / b.sd), 2)                AS median_sigma_ratio
FROM base b
JOIN limits l USING (sensor);
