-- Build: zwin. Each usable reading as a z-score inside its OWN 100-run window.
-- Used for the "same-period" separation score, which removes slow drift between windows.
CREATE TABLE zwin AS
SELECT r.sensor, r.run_id, w.is_fail, w.win, r.value,
       (r.value - avg(r.value) OVER ws) / nullif(stddev_samp(r.value) OVER ws, 0) AS z_window
FROM readings r
JOIN usable u USING (sensor)
JOIN run_windows w USING (run_id)
WINDOW ws AS (PARTITION BY r.sensor, w.win);
