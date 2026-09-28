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
2. Added deterministic streamed synthetic HTML/manifest/ground truth for six observed DB template families, nine defect types and reserved clean controls. Default ceiling 500; explicit generator limit may reach 5,000, but local evaluation remains ≤500. Metrics will use frozen existing confidence policy.
3. Added current process-tree RSS/system-pressure guard, batch shrink → one pause → abort, immediate swap-growth abort, stage peaks, measured 8/16/32/64 submission autotuning, process-wide model owner lock, CPU-process rejection before MLX import, bounded caches and queue backpressure. Sampling can detect swap growth, not prevent OS paging between observations; allocation headroom is checked before inference. No claim of an absolute OS-level no-swap guarantee.
4. Added range-addressed SQLite stage storage with atomic resumable chunks, pure CPU transforms, submit-batch inference protocol, CPU-only Dockerfile and cloud interface documentation. Postgres/object store/remote checkpoint conversion remain deliberately unimplemented. Legacy evidence remains bounded to 500 pages; distributed global reductions are documented prerequisites, not claimed finished infrastructure.
5. Added SQL-streamed compatibility candidates, exact normalized prompt/version/checkpoint cache keys, structural family partition metadata, local submit-batch MLX service and durable explicit class membership/fan-out. Dynamic evidence and outliers are not erased to manufacture deduplication: identical decisions take priority over a larger reduction ratio.
6. Added one-file-at-a-time unit checks for stratification, route separation, deterministic generated HTML/labels/orphans, guard shrink/pause/abort, swap detection, autotune, chunk resume/invalidation, old/new candidate prompt equivalence, explicit fan-out and CPU import isolation. Session conftest raises RLIMIT_NOFILE to 10240. Integrated streaming candidates and persistence into Pass 4; bounded offline 500-URL preparation is running before any model load.

7. Measured 500-URL CPU preparation (4.139 s, 176.078 MiB peak), 1,207/1,207 exact prompt matches and 0% extra prompt deduplication. MLX guard aborted on swap growth after 1.242 s at 944.016 MiB, before any candidate decision completed. No inference retry. One 480-URL synthetic CPU run: 2.098 s, 49.750 MiB, 184 clean controls. Added per-stage normalization and explicitly conditional 50k/500k/5M CPU projections in SCALING.md; no invented inference cost, accuracy, speedup or safe-batch result. Model choice/gate equivalence, precision/recall and autotuning remain blocked pending a safe host.

Follow-up correctness: wired class-level work orders and durable member IDs into Pass 5; bounded legacy worker result retention; routed the old probe through the single-owner guarded backend; distinguished deduplication from cache hits; added safe-host resume and explicit live equivalence test. CPU checks pass one file at a time; live inference check is skipped, not reported passing.
