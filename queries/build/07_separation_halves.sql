-- Build: separation_half. The same-period t computed separately on the first half
-- (runs 1-783, half A) and the second half (runs 784-1567, half B).
CREATE TABLE separation_half AS
SELECT sensor,
       CASE WHEN run_id <= 783 THEN 'A' ELSE 'B' END AS half,
       count(*) FILTER (WHERE is_fail = 1)           AS n_fail,
       (avg(z_window) FILTER (WHERE is_fail = 1) - avg(z_window) FILTER (WHERE is_fail = 0))
         / sqrt(var_samp(z_window) FILTER (WHERE is_fail = 1) / count(z_window) FILTER (WHERE is_fail = 1)
              + var_samp(z_window) FILTER (WHERE is_fail = 0) / count(z_window) FILTER (WHERE is_fail = 0)) AS t_same
FROM zwin
WHERE z_window IS NOT NULL
GROUP BY sensor, half;
