# LAYA PROGRESS

## Done
- Baseline measured, documented (docs/LAYA_BASELINE.md), and probed on 200 candidates (docs/LAYA_CONFIDENCE.md).
- Strict MLX-only analyzer with heads validation, gating policy, and persistence wired into Pass 4.
- Pass 5 verification runner wired to stored page evidence and Pass 6 reporting scoped by run_id.
- Fixed ulimit / file descriptor limits and test suite passes cleanly without crashes.
- Step 2: Verified small run (`crawl_20260928_144534`), laya_decisions complete, provenance & verifications written.
- Step 3: Implemented idempotent scripts/reset_legacy_laya.py, confirmed stale checkpoint alias logic.
- Step 4: Replay verification on identical crawl confirmed 100% cache hits and 0 inference calls.

## In Progress / Notes
- Historical full-site work stopped; no crawl/model processes running at new-direction start.
- Step 6: grep verified zero fallback/mock/api backend in decision path; test suite green.


## Bounded development direction
1. Added default dev profile, environment resource limits, deterministic stratified DB sample isolation, and disabled full-site benchmark. No crawl is started in dev. Templates with fewer than 3 members retain all available; impossible coverage fails explicitly.
