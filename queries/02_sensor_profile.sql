-- Q2. Of the 590 sensors, how many can be charted at all?
-- Each sensor lands in exactly one category, tested top to bottom (first match wins).
-- n = runs where the sensor was measured, d = number of different values it took.

WITH s AS (
    SELECT sensor, count(*) AS n, count(DISTINCT value) AS d
    FROM readings
    GROUP BY sensor
)
SELECT CASE WHEN d = 1                                        THEN '1 constant (one value only)'
            WHEN n < 0.9 * 1567                               THEN '2 measured in under 90% of runs'
            WHEN d < 10                                       THEN '3 fewer than 10 different values'
            WHEN sensor IN (SELECT sensor FROM usable)        THEN '5 usable'
            ELSE                                                   '4 other (too little baseline data)'
       END       AS category,
       count(*)  AS sensors
FROM s
GROUP BY 1
ORDER BY 1;
