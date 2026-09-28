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

## Projections only — no scale runs

Linear single-worker CPU scenarios, holding the measured work mix constant. They
exclude Laya, network crawl, remote storage, global reducers, work orders and reports.
A 500-URL sample cannot establish cache behavior or template distribution at scale.
The synthetic timings describe fixture generation/parsing, not a production audit.
No total end-to-end completion time can be projected responsibly before model timing.

| URLs | Real ingest + evidence + candidates (projected) | Synthetic generation + evidence (projected) | CPU memory scenario |
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

## Remaining verification and safe-host resume

The MLX evaluation is blocked by system swap growth on the current host. Leave the
confidence policy and checkpoint unchanged. On a host with sufficient free memory,
resume the recorded evaluation, reusing the existing synthetic directory:

```sh
.venv/bin/python scripts/evaluate_laya_dev.py \
  --prepared reports/laya-dev-500/prepared.json \
  --output reports/laya-dev-evaluation --resume \
  --synthetic-dir reports/laya-dev-synthetic-cpu/site
SEOJEV_EQUIVALENCE_REPORT=reports/laya-dev-evaluation/measurements.json \
  .venv/bin/python -m pytest -q tests/test_dev_equivalence.py
```

The runner compares independent old/new model choice+gate results, keeps labels out
of model inputs, and writes partial results on abort. Its 8/16/32/64 autotune measures
bounded submission chunks with the scalar checkpoint API; it does not claim native
cross-page tensor batching. Resume does not regenerate the planted test set. A
completed report is mandatory for the live equivalence test to pass.

Before cloud scale: implement Postgres/object-store adapters and global reducers;
configure worker/memory/queue sizes from actual measurements; implement the remote
submit-batch boundary using a conversion of this SAME checkpoint; validate all heads
and 500-URL choice+gate equivalence again. Do not deploy the compatibility island on
more than 500 URLs. No cloud infrastructure was built.
