-- Q11. In which windows did many sensors START an excursion at the same time?
-- An onset = a flagged excursion (3+ Rule 1 points) where the same sensor was NOT flagged in the window before.
-- Many onsets in one window = a common cause is plausible (an equipment change, a new lot, a recipe step).
-- Window 4 counts every sensor flagged in it, because windows 1-3 are baseline and are not in the log.
-- ADDED AFTER SEEING Q9 and Q10 (most excursions persisted), so this is exploration, not a pre-stated rule.

WITH onsets AS (
    SELECT c.win, count(*) AS onsets
    FROM capa c
    WHERE NOT EXISTS (SELECT 1 FROM capa p WHERE p.sensor = c.sensor AND p.win = c.win - 1)
    GROUP BY c.win
),
w AS (
    SELECT win, min(ts)::DATE AS first_day, max(ts)::DATE AS last_day,
           round(100.0 * sum(is_fail) / count(*), 1) AS fail_pct
    FROM run_windows
    GROUP BY win
)
SELECT w.win, w.first_day, w.last_day, w.fail_pct,
       lag(w.fail_pct) OVER (ORDER BY w.win)  AS prev_fail_pct,
       coalesce(o.onsets, 0)                  AS sensors_starting_excursion
FROM w
LEFT JOIN onsets o USING (win)
WHERE w.win >= 4
ORDER BY w.win;
