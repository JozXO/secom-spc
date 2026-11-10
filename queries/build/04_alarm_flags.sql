-- Build: flags. One row per usable sensor reading, with the three alarm rules (RULES.md).
--   z = (value - centre) / sigma, using the baseline limits.
--   rule1: |z| > 3
--   rule2: this point completes 9+ values in a row on the same side of the centre line
--   rule5: this point is beyond 2 sigma and at least 2 of the last 3 points are beyond 2 sigma, same side
-- The windows below look at the previous 8 (or 2) rows of the SAME sensor in run order.
CREATE TABLE flags AS
WITH z AS (
    SELECT r.sensor, r.run_id, w.win, w.in_baseline, r.value,
           (r.value - l.centre) / l.sigma AS z
    FROM readings r
    JOIN limits l USING (sensor)
    JOIN run_windows w USING (run_id)
),
side AS (
    SELECT *, CASE WHEN z > 0 THEN 1 WHEN z < 0 THEN -1 ELSE 0 END AS side
    FROM z
),
roll AS (
    SELECT *,
           min(side)  OVER w9 AS min9,
           max(side)  OVER w9 AS max9,
           count(*)   OVER w9 AS n9,
           sum(CASE WHEN z >  2 THEN 1 ELSE 0 END) OVER w3 AS hi3,
           sum(CASE WHEN z < -2 THEN 1 ELSE 0 END) OVER w3 AS lo3
    FROM side
    WINDOW w9 AS (PARTITION BY sensor ORDER BY run_id ROWS BETWEEN 8 PRECEDING AND CURRENT ROW),
           w3 AS (PARTITION BY sensor ORDER BY run_id ROWS BETWEEN 2 PRECEDING AND CURRENT ROW)
)
SELECT sensor, run_id, win, in_baseline, value, z,
       abs(z) > 3                                         AS rule1,
       (n9 = 9 AND min9 = max9 AND min9 <> 0)             AS rule2,
       ((z > 2 AND hi3 >= 2) OR (z < -2 AND lo3 >= 2))    AS rule5
FROM roll;
