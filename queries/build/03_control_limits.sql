-- Build: limits. Individuals (I) chart limits per usable sensor, from the baseline only.
--   centre = mean of baseline values
--   sigma  = average moving range / 1.128   (moving range = |this value - previous value|)
--   UCL / LCL = centre +/- 3 sigma
-- LAG looks at the previous MEASURED value of that sensor (missing values have no row).
CREATE TABLE limits AS
WITH ordered AS (
    SELECT r.sensor, r.run_id, r.value, w.in_baseline,
           abs(r.value - lag(r.value) OVER (PARTITION BY r.sensor ORDER BY r.run_id)) AS moving_range
    FROM readings r
    JOIN run_windows w USING (run_id)
    WHERE r.sensor IN (SELECT sensor FROM usable)
),
base AS (
    SELECT sensor,
           avg(value)        FILTER (WHERE in_baseline) AS centre,
           avg(moving_range) FILTER (WHERE in_baseline) / 1.128 AS sigma
    FROM ordered
    GROUP BY sensor
)
SELECT sensor, centre, sigma,
       centre + 3 * sigma AS ucl,
       centre - 3 * sigma AS lcl
FROM base
WHERE sigma > 0;
