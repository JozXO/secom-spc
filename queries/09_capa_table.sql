-- Q9. CAPA-style table: the 12 biggest flagged excursions (sensor-windows with 3+ Rule 1 points).
-- next_window: did the same sensor drop below 3 Rule 1 points in the next window?
-- fail_pct / next_fail_pct: the line fail rate in the flagged window and the one after.
-- in_top20: is the sensor also in the top 20 of the pass/fail ranking (Q6)?
-- This records association only. It does not show that the sensor caused any failure.

SELECT sensor, win, first_day, last_day, r1_hits, next_window_hits, next_window,
       fail_pct, next_fail_pct, rank_same, in_top20
FROM capa
ORDER BY r1_hits DESC, sensor, win
LIMIT 12;
