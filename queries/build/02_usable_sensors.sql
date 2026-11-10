-- Build: usable. The sensors that are charted at all (the four conditions in RULES.md).
-- readings has no row for a missing value, so count(*) = runs where the sensor was measured.
CREATE TABLE usable AS
SELECT r.sensor,
       count(*)                                                  AS n_measured,
       count(DISTINCT r.value)                                   AS n_distinct,
       count(*) FILTER (WHERE w.in_baseline)                     AS n_baseline,
       stddev_samp(r.value) FILTER (WHERE w.in_baseline)         AS sd_baseline
FROM readings r
JOIN run_windows w USING (run_id)
GROUP BY r.sensor
HAVING count(*) >= 0.9 * 1567                                   -- 1. measured in 90%+ of all runs
   AND count(*) FILTER (WHERE w.in_baseline) >= 270             -- 2. 270+ of the 300 baseline runs
   AND count(DISTINCT r.value) >= 10                            -- 3. not an on/off or status column
   AND stddev_samp(r.value) FILTER (WHERE w.in_baseline) > 0;   -- 4. baseline is not constant
