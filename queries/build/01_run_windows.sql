-- Build: run_windows. One row per run with its 100-run window and a baseline flag.
-- 1 + (run_id - 1) // 100 : runs 1-100 -> window 1, runs 101-200 -> window 2, ...
-- Baseline = first 300 runs (windows 1-3). See RULES.md.
CREATE TABLE run_windows AS
SELECT run_id,
       ts,
       is_fail,
       1 + (run_id - 1) // 100 AS win,
       run_id <= 300           AS in_baseline
FROM runs;
