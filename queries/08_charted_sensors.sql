-- Q8. Which four sensors get drawn? (RULES.md: pick rule fixed in advance)
--   3 sensors with the highest same-period |t|, plus 1 well-behaved comparison sensor:
--   the usable sensor with the fewest alarm points of any rule in monitoring (lowest sensor number breaks a tie).

WITH alarms AS (
    SELECT sensor, sum((rule1 OR rule2 OR rule5)::INT) AS alarm_points
    FROM flags
    WHERE NOT in_baseline
    GROUP BY sensor
),
top3 AS (
    SELECT sensor, 'top 3 by same-period |t|' AS why
    FROM separation
    ORDER BY rank_same, sensor
    LIMIT 3
),
quiet AS (
    SELECT sensor, 'fewest alarm points in monitoring' AS why
    FROM alarms
    ORDER BY alarm_points, sensor
    LIMIT 1
),
picked AS (
    SELECT * FROM top3 UNION ALL SELECT * FROM quiet
)
SELECT p.sensor, p.why, a.alarm_points, s.rank_same, round(s.t_same, 2) AS t_same
FROM picked p
JOIN alarms a USING (sensor)
JOIN separation s USING (sensor)
ORDER BY CASE WHEN p.why LIKE 'top%' THEN 0 ELSE 1 END, s.rank_same;
