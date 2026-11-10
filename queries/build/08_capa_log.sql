-- Build: capa. Every flagged excursion = one sensor in one monitoring window with 3+ Rule 1 alarm points.
-- For each: did the NEXT window recover (fewer than 3 Rule 1 points for the same sensor)?
-- A sensor-window with no alarm has no row in `hits`, so the join to the next window uses coalesce(..., 0).
CREATE TABLE capa AS
WITH hits AS (
    SELECT sensor, win, count(*) AS r1_hits
    FROM flags
    WHERE rule1 AND NOT in_baseline
    GROUP BY sensor, win
),
win_yield AS (
    SELECT win, min(ts)::date AS first_day, max(ts)::date AS last_day,
           count(*) AS runs, sum(is_fail) AS fails,
           round(100.0 * sum(is_fail) / count(*), 1) AS fail_pct
    FROM run_windows
    GROUP BY win
)
SELECT h.sensor, h.win, y.first_day, y.last_day, h.r1_hits,
       coalesce(n.r1_hits, 0)                                   AS next_window_hits,
       CASE WHEN h.win = (SELECT max(win) FROM win_yield) THEN 'no next window'
            WHEN coalesce(n.r1_hits, 0) < 3                    THEN 'recovered'
            ELSE 'persists' END                                 AS next_window,
       y.fail_pct, yn.fail_pct AS next_fail_pct,
       s.rank_same, s.rank_same <= 20                           AS in_top20
FROM hits h
JOIN win_yield y        ON y.win  = h.win
LEFT JOIN hits n        ON n.sensor = h.sensor AND n.win = h.win + 1
LEFT JOIN win_yield yn  ON yn.win = h.win + 1
JOIN separation s       ON s.sensor = h.sensor
WHERE h.r1_hits >= 3;
