-- Build: separation. How well each usable sensor separates fail runs from pass runs.
--   t_raw  : Welch t on the raw values, fail minus pass (all runs)
--   t_same : Welch t on the within-window z-scores (same-period comparison)
--   auc    : area under the ROC curve from average ranks; 0.5 = no separation,
--            above 0.5 = fail runs read higher
-- Welch t = (mean_fail - mean_pass) / sqrt(var_fail/n_fail + var_pass/n_pass)
CREATE TABLE separation AS
WITH ranked AS (
    SELECT sensor, is_fail, value, z_window,
           rank() OVER (PARTITION BY sensor ORDER BY value)
             + (count(*) OVER (PARTITION BY sensor, value) - 1) / 2.0 AS avg_rank   -- ties share the middle rank
    FROM zwin
),
agg AS (
    SELECT sensor,
           count(*)        FILTER (WHERE is_fail = 1) AS n_fail,
           count(*)        FILTER (WHERE is_fail = 0) AS n_pass,
           avg(value)      FILTER (WHERE is_fail = 1) AS mean_fail,
           avg(value)      FILTER (WHERE is_fail = 0) AS mean_pass,
           var_samp(value) FILTER (WHERE is_fail = 1) AS var_fail,
           var_samp(value) FILTER (WHERE is_fail = 0) AS var_pass,
           count(z_window) FILTER (WHERE is_fail = 1) AS zn_fail,
           count(z_window) FILTER (WHERE is_fail = 0) AS zn_pass,
           avg(z_window)   FILTER (WHERE is_fail = 1) AS zmean_fail,
           avg(z_window)   FILTER (WHERE is_fail = 0) AS zmean_pass,
           var_samp(z_window) FILTER (WHERE is_fail = 1) AS zvar_fail,
           var_samp(z_window) FILTER (WHERE is_fail = 0) AS zvar_pass,
           sum(avg_rank)   FILTER (WHERE is_fail = 1) AS rank_sum_fail
    FROM ranked
    GROUP BY sensor
),
scored AS (
    SELECT sensor, n_fail, n_pass, mean_fail, mean_pass,
           (mean_fail - mean_pass) / sqrt(var_fail / n_fail + var_pass / n_pass)          AS t_raw,
           (zmean_fail - zmean_pass) / sqrt(zvar_fail / zn_fail + zvar_pass / zn_pass)    AS t_same,
           (rank_sum_fail - n_fail * (n_fail + 1) / 2.0) / (n_fail * n_pass)              AS auc
    FROM agg
)
SELECT *,
       rank() OVER (ORDER BY abs(t_raw)  DESC) AS rank_raw,
       rank() OVER (ORDER BY abs(t_same) DESC) AS rank_same
FROM scored;
