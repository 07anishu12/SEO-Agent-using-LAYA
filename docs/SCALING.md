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
owns the MLX lock. It terminates immediately on any swap-out/occupancy increase,
pressure above normal, or configured RSS/available-memory limit violation.

| Trial | Elapsed | Observed peak RSS | Swap occupancy before → after | Swap-out delta | Result |
|---|---:|---:|---:|---:|---|
| Submission batch 8 | 0.988 s | 940.875 MiB | 1,018.563 → 1,018.563 MiB | +0.140625 MiB | UNSAFE; terminated |
| 16 / 32 / 64 | Not attempted | Unmeasured | Unmeasured | Unmeasured | Stopped after unsafe 8 |

Spawn baseline RSS was 0.594 MiB; the terminated trial did not retain a Python
pre-model baseline. The runner now persists that baseline before model loading for
future trials. Maximum sampled system memory use was 69.5%; macOS pressure stayed
normal (1); minimum available memory was 5,002.266 MiB. Process RSS was below the
4,096 MiB budget. Nevertheless, the strict zero-swap-growth guard rejected the run.
The small page-out cannot be attributed to MLX versus background OS activity.
Sampling is not an OS guarantee against paging between observations.

**Safe batch: NONE.** The model was not retried. Inspection found that MLX's unused
allocator cache defaults to its generous device memory limit. Unused buffer caching
is now disabled, unused buffers are released after loading/prediction, and failed
startup releases model ownership. No dtype, checkpoint, prompt, question batch,
threshold or gate changed. This lifecycle change is CPU-tested but has not been
measured with the model; it is not claimed to resolve the observed page-out.

Choice+gate equivalence: **0 completed comparisons; blocked**, with 1,207 candidate
identities outstanding. Prompt equality remains 1,207/1,207 from the prior bounded
preparation. The updated harness runs the old worker implementation from 896b2dd,
counts each head separately, and stops on the first mismatch/missing decision.
Synthetic TP/FP/TN/FN, precision/recall and successful end-to-end dev runtime remain
**unmeasured**. Ground-truth scoring now streams the existing JSON entries and reports
per-label validation recall without misrepresenting it as localization accuracy.

The prior CPU tables and PROJECTION scenarios remain valid only for their measured
CPU work. No end-to-end, inference throughput, successful model RSS or cloud dollar
projection can be derived from this failed trial. Do not treat the historical CPU
preparation time as a completed dev runtime.

## Safe-host procedure — blocked on this host, not authorization to retry

After a materially different host/resource condition is available, run a fresh
cold-process autotune into a new output directory. Do not continue if batch 8 fails.
A successful report is required before the externally guarded evaluator can start:

```sh
.venv/bin/python scripts/laya_acceptance.py autotune \
  --prepared reports/laya-dev-500/prepared.json \
  --output reports/laya-autotune-safe-host
# Only if the report contains a measured safe batch:
.venv/bin/python scripts/laya_acceptance.py evaluate \
  --prepared reports/laya-dev-500/prepared.json \
  --autotune-report reports/laya-autotune-safe-host/autotune.json \
  --output reports/laya-acceptance-evaluation \
  --synthetic-dir reports/laya-dev-synthetic-cpu/site
```

This does not regenerate the synthetic set. Original confidence policy and checkpoint
are mandatory. Full dev end-to-end measurement remains a separate acceptance step
once model equivalence and synthetic evaluation succeed; it has not run here.

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
