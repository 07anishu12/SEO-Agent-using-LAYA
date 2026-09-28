# Laya repair baseline — 2026-09-28

Starting commit: `3f1b958`. Branch: `fix/laya-pipeline`.
Preserved pre-existing user modification: `data/site-profile.json`.
SQLite online backup: `data/seo.db.bak-20260928-141754` (not committed).

Command: `.venv/bin/python3 -m pytest -q`.
Result: **109 passed, 5 failed, 71 errors**, 15.76 seconds.
Most errors: PostgreSQL localhost:5432 connection refused. Failures also include
dev-stack lifecycle and Playwright browser availability. These predate changes.

Installed environment: macOS arm64; laya-mlx 0.2.0, mlx 0.32.2, numpy 2.5.3.
Live cache table has 19 columns while the worker writes 27. The latest saved
P4_CALIBRATION checkpoint records 18 candidates, zero decisions, zero errors.
Current stage names differ from this historical checkpoint.

Read-only baseline reproduction:
`.venv/bin/python3 scripts/diagnose_laya.py`.

Baseline counts: 11,452 opportunities, all unvalidated; 11 legacy fake stamps;
4,333 historical decisions, all missing v2 provenance; zero cache rows;
11,364 historical work orders and 55 verifications. Thus the audit's claim of
zero work orders/verification globally is false; it applies to particular runs.
The audit's 16 decisions refers to individual recent runs, not the entire DB.
Some existing initialization tests write empty crawl runs to the live database;
use the backup or an explicit run ID when comparing the baseline.

## Historical causes verified in git

`5fee378:laya/worker_pool.py` calls `task_done()` immediately after dequeue,
before inference. `queue.join()` can therefore return with zero completed
decisions; `stop()` then cancels the workers. The historical checkpoint for
`crawl_20260927_181935` records exactly this: 18 candidates, zero decisions.
`5fee378:engine/pipeline.py` stamps unmatched opportunities with `optimize`,
0.85 and `dec_laya_<opportunity prefix>`. This is the source of the 11 fake
rows, not Pass 3. Both code defects were already changed by `3f1b958`, but
neither historical data nor a completion-count invariant was repaired.

Current opportunity key expressions are equal, but duplicated. Cluster results
are stored without being propagated to their synthesized opportunities.
Current checkpoint lookup uses exact names: old P4_CALIBRATION cannot skip
P4_LAYA_DECISION_ENGINE. However, same-name checkpoints have no model/prompt
or persisted-result validation, and checkpoint SQL failures are swallowed.

The installed runtime exposes one `LayaSEOAnalyzer`; there is no second
`LayaAnalyzer` implementation in the current tree. Old documentation is stale.

After starting PostgreSQL/Redis/MinIO test infrastructure, a second unchanged
suite run reported **164 passed, 3 failed, 18 errors** in 343.50s. Browser
installation finished during that run; missing-browser and frontend startup
failures remained. MLX runs natively on the host; only test services use Docker.
