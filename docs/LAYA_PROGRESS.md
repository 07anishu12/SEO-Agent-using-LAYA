# LAYA PROGRESS

## Done
- Baseline measured, documented (docs/LAYA_BASELINE.md), and probed on 200 candidates (docs/LAYA_CONFIDENCE.md).
- Strict MLX-only analyzer with heads validation, gating policy, and persistence wired into Pass 4.
- Pass 5 verification runner wired to stored page evidence and Pass 6 reporting scoped by run_id.
- Fixed ulimit / file descriptor limits and stage test assertions; resolved MLX cache replay consistency.

## Todo
- Step 2: Read /tmp/seojev-laya-small.log, run diagnose_laya.py on small run, verify non-null fields & verification rows.
- Step 3: Write scripts/reset_legacy_laya.py, reset 11 legacy fake stamps, revalidate opportunities on existing crawl.
- Step 4: Re-crawl / replay test verifying cache hit > 0 and 0 inference on identical run.
- Step 5: Final full crawl of drivio.in, report acceptance/review/suppression stats.
- Step 6: Verify no fallback/mock in path via grep, run tests, push.
