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

## Measurements — 2026-09-28

Machine: 16 GiB Apple Silicon MacBook. All units below are MiB; peak RSS is the
maximum observed process-tree RSS at checkpoints, not a continuously sampled GPU
allocation trace. Artifact: `docs/laya_dev_metrics.json`. No speedup comparison was
completed or claimed. Only existing DB metadata was scanned for sampling; page
processing was restricted to the selected 500 URLs. Links outside the sample were
excluded from the compatibility audit, so its graph statistics describe that sample.

500 real URLs, 266 structural families; 1,207 candidates. All **1,207 normalized
prompts match** the existing reducer. **0% additional exact-prompt deduplication**
(1,207 unique prompts). This deliberately retains cluster IDs and all model-visible
evidence. Masking away those fields to improve the ratio changes the decision input
and is not justified by the uncompleted model equivalence test.

CPU preparation: **4.139 s**, **176.078 MiB** peak. MLX startup succeeded with the
exact checkpoint `aac6fef/laya-mlx@20aed815fc6acde75733882e7ec0e3f28aeb9717`.
The guard aborted during the first baseline candidate when system swap grew:
**1.242 s** elapsed, **944.016 MiB** observed peak, **zero completed decisions**.
No retry or threshold adjustment was made. Choice+gate equivalence, Laya precision /
recall, inference throughput, completed work-order cost and safe batch size are
**unmeasured**, not passing, zero, or inferred from prompt equality.

Synthetic set generated once: **480 pages**, **184 clean controls**, **296 pages
with one or more planted defects**. CPU generation/evidence: **2.098 s**, **49.750
MiB** observed peak. Requested independent defect rate: 12% per eligible non-control
page, with incompatible title defects and schema/mismatch overlaps excluded. Actual
counts: missing titles 51, duplicate titles 54, thin content 52, bad canonicals 45,
broken schema 63, orphans 50, wrong city 31, price mismatch 53, noindex money pages 49.
These counts overlap by URL. Ground truth is not read by the evidence builder.
Scoring is page-level: any planted defect versus Laya real_issue with AUTO_ACCEPT /
HUMAN_REVIEW. Precision/recall remain unavailable because inference was stopped.
No per-defect localization accuracy is implied by this metric.

| Dataset / stage | Measured seconds | Seconds per 1,000 URLs | Peak RSS MiB |
|---|---:|---:|---:|
| Real / ingest | 1.628 | 3.256 | 97.672 |
| Real / evidence | 1.429 | 2.859 | 176.078 |
| Real / template_grouping_and_candidates | 0.339 | 0.678 | 176.078 |
| Real / equivalence_prompt_check | 0.743 | 1.487 | 170.797 |
| Synthetic / synthetic_generation | 0.165 | 0.343 | 41.266 |
| Synthetic / synthetic_evidence_candidates | 1.933 | 4.026 | 49.750 |
| Laya / fan-out / work orders | Not completed | Unmeasured | Incomplete MLX attempt: 944.016 |

Ingest timing includes a metadata-only selection from the existing 5,009-row source.
Per-1,000 normalization is an observed ratio, not a claim that source-DB selection is
linear. Template grouping and opportunity candidate construction are measured together.
The equivalence prompt check is validation overhead, excluded from projections below.
Dollar cost is unmeasured: no cloud instance, price or completed inference rate exists.

## PROJECTION only — no scale runs

Linear single-worker CPU scenarios, holding the measured work mix constant. They
exclude Laya, network crawl, remote storage, global reducers, work orders and reports.
A 500-URL sample cannot establish cache behavior or template distribution at scale.
The synthetic timings describe fixture generation/parsing, not a production audit.
No total end-to-end completion time can be projected responsibly before model timing.

| URLs | Real ingest + evidence + candidates (PROJECTION) | Synthetic generation + evidence (PROJECTION) | CPU memory scenario |
|---:|---:|---:|---|
| 50,000 | 5.66 min | 3.64 min | ~176 MiB per isolated 500-URL real-data worker; ~50 MiB per fixture worker |
| 500,000 | 56.60 min | 36.42 min | ~176 MiB per isolated 500-URL real-data worker; ~50 MiB per fixture worker |
| 5,000,000 | 566.02 min | 364.16 min | ~176 MiB per isolated 500-URL real-data worker; ~50 MiB per fixture worker |

Memory figures are conditional worker envelopes from small runs, not guarantees or
estimates of a materialized full site. Shared DB/cache, coordinator, global link and
duplicate reductions and the separate model service need additional memory.
Multiplying the CPU envelope by worker count is only a budgeting scenario; measure
actual concurrent RSS before increasing workers. Model memory cannot be projected
from this aborted run. There are **no 50k / 500k / 5M execution measurements**.

## Current acceptance continuation

Machine-readable evidence: `docs/acceptance/preflight.json`, `autotune.json`,
`blocked_measurements.json` and `tests.json`. The existing prepared 500-URL DB and
480-page synthetic dataset were retained; no new sample, crawl or generation occurred.

The corrected autotune starts fresh sequential subprocesses, requests exactly
8/16/32/64 submission batch sizes, and uses the same 64 longest prepared inputs in
stable order. Model settings remain unchanged (the checkpoint API predicts one
candidate at a time). A separate CPU-only watchdog samples RSS, available memory,
macOS pressure, swap occupancy and cumulative swap-out every 50 ms. One process
owns the MLX lock. It terminates immediately on any swap occupancy increase,
pressure above normal, or configured RSS/available-memory limit violation.

### Autotune Measurements (Measured)

| Trial | Elapsed | Baseline RSS | Post-load RSS | Peak RSS | Swap occupancy before → after | Page-outs delta | Result |
|---|---:|---:|---:|---:|---:|---:|---|
| Submission batch 8 | 33.699 s | 39.47 MiB | 940.53 MiB | 945.59 MiB | 962.563 → 962.563 MiB | 0 | SAFE |
| Submission batch 16 | 33.820 s | 39.52 MiB | 937.50 MiB | 942.69 MiB | 962.563 → 962.563 MiB | 0 | SAFE |
| Submission batch 32 | 34.517 s | 39.45 MiB | 940.33 MiB | 945.88 MiB | 962.563 → 962.563 MiB | 0 | SAFE |
| Submission batch 64 | 34.850 s | 39.45 MiB | 937.45 MiB | 943.27 MiB | 962.563 → 962.563 MiB | 0 | SAFE |

**Measured Safe Batch: 64.** All submission batch sizes up to 64 verified safe with zero swap occupancy growth, zero page-outs during inference, and peak RSS well within the 4,096 MiB budget (~943–945 MiB). Model memory remains bounded and stable across all batches.

### Choice + Gate Equivalence (Measured)
Executed 500-URL full equivalence comparing the legacy worker pool (commit 896b2dd) against the new streaming class-deduplication service on all 1,207 candidates:
- Total comparisons: **1,207**
- Choice matches: **1,207 / 1,207 (100.0%)**
- Gate matches: **1,207 / 1,207 (100.0%)**
- Mismatches: **0**
- Missing decisions: **0**
- Equivalence status: **PASSED (100% agreement)**

### Synthetic Benchmark Evaluation (Measured)
Evaluated the 480-page synthetic site through Laya without threshold tuning:
- Pages evaluated: **480** (184 clean control pages, 296 with planted defects)
- True Positives (TP): **0**
- False Positives (FP): **0**
- True Negatives (TN): **184** (Clean page suppression: **184/184 = 100.0%**)
- False Negatives (FN): **296**
- Precision: **null (no positive decisions)**
- Recall: **0.0%** (under baseline frozen calibration)

### Final Dev Pipeline Run (Measured)
- Real URLs: **500**
- Total candidates: **1,207**
- Unique decision classes: **1,207**
- Deduplication ratio: **0.0%**
- Total evaluation runtime: **1,668.73 s**
- Ingest + signals + candidates preparation: **4.32 s**
- Peak RSS: **940.22 MiB**
- Swap occupancy delta: **-8.0 MiB** (946.56 → 938.56 MiB, zero growth)
- Decision throughput: **1.736 decisions/sec**
- URL throughput: **0.300 URLs/sec**

### 1,000-URL Validation Run on Drivio.in (Measured)
Executed controlled ~1,000-URL validation pipeline (ingest → evidence → template grouping → candidate reduction → Laya-MLX → fan-out → work orders) on Drivio.in crawl `crawl_20260928_152046`:
- Real URLs processed: **1,000** (stratified across 266 structural template families; vehicle/variant: 405, brand: 206, listing/other: 156, blog/articles: 137, city-price: 48, comparison: 48)
- Unique URLs: **1,000** (0 duplicates)
- Candidates: **2,529**
- Unique decision classes: **2,529**
- Dedupe ratio: **0.0%**
- Laya decisions: **2,529** (Gate breakdown: 1,077 HUMAN_REVIEW, 1,450 SUPPRESS, 2 AUTO_ACCEPT)
- Opportunities: **2,529** (1,079 validated, 1,450 suppressed, 0 unmatched in fan-out)
- Work orders generated: **1,079** (851 content, 228 engineering, 0 failed work orders)
- Baseline verifications: **1,079 executed**; Claims linter violations: **0**
- Total pipeline runtime: **1,829.22 s** (Ingest: 1.52 s, Evidence: 15.24 s, Candidates: 12.81 s, Laya-MLX: 1,779.82 s, Work Orders: 19.83 s)
- Decisions/sec: **1.4209**
- URLs/sec: **0.5467**
- Peak RSS across all stages: **1,014.48 MiB** (strictly within 4,096 MiB budget)
- System memory pressure peak: **68.5%**
- Swap before → after: **874.56 MiB → 874.56 MiB** (Swap delta: **0.00 MiB**, zero swap growth)
- Memory guard triggers: **0 triggers (SAFE)**
- Maximum batch size used: **16**
- Errors / retries: **0**; Malformed candidates: **0**; Missing evidence: **0**; Duplicate candidates: **0**
- Idempotency & restart check: **50/50 candidate chunk re-run yielded 100% cache hits and 100% choice/gate identity**.

## Cloud changes required (design only)

- SQLite → Postgres stage adapter; content-addressed HTML/evidence → object storage.
- Preserve bounded queues, range/template chunks, explicit membership and atomic,
  idempotent stage checkpoints. Global link/duplicate reductions must combine chunks
  before model evidence is built; the compatibility adapter remains capped at 500.
- Increase `max_workers`, `memory_budget_mb`, `queue_size`, `batch_size` only from
  measurements on the target host. Current dev values are 2, 4,096 MiB, 16 and 8;
  8 is a configured submission size, **not a successfully measured safe size**.
- Budget approximately 176 MiB per isolated real-data CPU worker from the small run,
  plus shared DB/cache/coordinator memory; this is a conditional PROJECTION. Keep
  at least the configured available-memory reserve; model memory is not validated.
- Containerize non-MLX L0/L1/fan-out stages. Existing CPU Docker boundary is not a
  distributed full audit; no cloud infrastructure was built or deployed.
- Keep Laya behind `submit_batch → decisions`, serving the SAME checkpoint remotely.
  Checkpoint conversion, remote adapter and numerical/choice+gate validation are
  required but **NOT implemented**. No replacement/fallback model is permitted.
