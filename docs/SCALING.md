# Bounded local work and future scaling

Development defaults to `--profile dev`: 500 URLs maximum, seeded structural-family
sampling from an existing crawl DB, at most two CPU workers, small chunks and a
configurable per-chunk sleep. Production must be explicitly selected. No full-site
run is part of development. Missing members are not fabricated: a family with one
or two URLs contributes all available. If minimum coverage cannot fit, sampling fails.

The original crawl has 423 stored template IDs requiring 686 URLs under a
min(3, available) policy. With user approval, stratification uses structural families,
retaining page type, static route suffixes, query keys and distinct route shapes.
Original template IDs remain in page evidence and Laya prompts.

## Configuration and boundaries

`SEOJEV_MEMORY_BUDGET_MB`, `SEOJEV_MAX_WORKERS`, `SEOJEV_BATCH_SIZE`,
`SEOJEV_QUEUE_SIZE`, `SEOJEV_THROTTLE_SECONDS`, `SEOJEV_PAUSE_SECONDS`,
`SEOJEV_MIN_AVAILABLE_MB`, `SEOJEV_MAX_URLS` and `SEOJEV_SEED` override profile values.
Dev caps still apply. Storage uses `SEOJEV_DB_PATH`, `SEOJEV_STORE_DIR` and
`SEOJEV_STORAGE_BACKEND`. SQLite is implemented; requesting another backend fails
explicitly. A future Postgres adapter implements the same stage-store contract;
large evidence blobs belong in an object store with content hashes as references.

`StageStore` provides keyed range iteration and atomic result/checkpoint writes.
Chunk transforms are deterministic functions of inputs; checkpoint identity includes
inputs and stage/checkpoint contract. Ingest → evidence → template grouping →
candidates → Laya → explicit membership fan-out → work orders are separate boundaries.
Cross-chunk duplicate and link statistics require global SQL reductions, not partial
per-chunk counts. The legacy evidence/opportunity implementation remains a bounded
≤500-page compatibility island; it must be replaced with these global reductions
before production-wide execution. Do not concatenate chunks into that implementation.

`DecisionService.submit_batch` accepts candidates and returns decisions. Local MLX
uses the same aac6fef/laya-mlx checkpoint, question set and confidence policy.
The installed checkpoint API performs scalar predictions; a batch is a bounded
submission chunk, not vectorized inference. One OS-locked process owns the model;
CPU workers fail before importing MLX. No alternative model or fallback is allowed.
A future remote adapter must serve the SAME checkpoint and preserve tokenizer,
heads, calibrated probabilities and gates. Conversion and equivalence validation
are prerequisites; neither remote serving nor conversion is implemented here.

The Dockerfile packages CPU-only ingest/evidence/fan-out chunk transport. It does
not include MLX. Example: `docker build -t seojev-cpu .`, then mount input/output
and invoke `ingest --input /data/input.jsonl --profile dev`. Legacy L0/L1 detectors
are not yet all converted to distributed reducers; this image is not a full audit.

Increase workers, memory and queue capacity on a larger host only after measuring.
Keep inference separate and model ownership singular per service. RSS includes
children. A pressure checkpoint shrinks the batch, pauses once, then aborts; swap
increase aborts immediately. OS paging between samples cannot be prohibited by
Python; conservative headroom and a larger host are needed for a strict no-swap SLO.

## Measurements

Pending guarded 500-URL sample and one ≤500-URL synthetic run. No speedup is claimed.
Projection tables will distinguish measured stages from unmeasured model/cloud cost.
