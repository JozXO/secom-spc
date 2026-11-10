-- Q6. Which sensors separate fail runs from pass runs best? Top 15 by the same-period Welch t.
-- t_same  : Welch t on within-window z-scores (the main score, see RULES.md)
-- t_raw   : Welch t on raw values; where this is much bigger than t_same, the sensor mostly drifts with time
-- auc     : 0.5 = no separation; above 0.5 fail runs read higher, below 0.5 lower
-- These are candidates to look at, not proof of cause.

SELECT rank_same,
       sensor,
       round(t_same, 2)                  AS t_same,
       round(t_raw, 2)                   AS t_raw,
       rank_raw,
       round(auc, 3)                     AS auc,
       round(mean_pass, 3)               AS mean_pass,
       round(mean_fail, 3)               AS mean_fail
FROM separation
ORDER BY rank_same, sensor
LIMIT 15;
