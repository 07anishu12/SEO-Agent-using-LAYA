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
