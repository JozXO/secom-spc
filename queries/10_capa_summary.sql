-- Q10. Summary of the CAPA log: how many flagged excursions, and what happened in the next window?
-- Also shows how many of them involve a sensor from the pass/fail top 20.

SELECT next_window,
       count(*)                              AS excursions,
       count(DISTINCT sensor)                AS sensors,
       count(*) FILTER (WHERE in_top20)      AS in_top20
FROM capa
GROUP BY next_window
ORDER BY next_window;
