-- Q7. Does the ranking hold up? Take the top 10 sensors from the first half of the runs (A: runs 1-783)
-- and look at how the same sensors score in the second half (B: runs 784-1567).
-- A sensor that is really tied to failures should keep its sign and a reasonable rank in half B.
-- With 415 sensors, a rank of about 207 is what a sensor with no relationship would get on average.

WITH a AS (
    SELECT sensor, t_same AS t_a, rank() OVER (ORDER BY abs(t_same) DESC) AS rank_a
    FROM separation_half WHERE half = 'A'
),
b AS (
    SELECT sensor, t_same AS t_b, rank() OVER (ORDER BY abs(t_same) DESC) AS rank_b
    FROM separation_half WHERE half = 'B'
)
SELECT a.sensor,
       rank_a, round(t_a, 2) AS t_first_half,
       rank_b, round(t_b, 2) AS t_second_half,
       sign(t_a) = sign(t_b) AS same_direction
FROM a JOIN b USING (sensor)
WHERE rank_a <= 10
ORDER BY rank_a;
