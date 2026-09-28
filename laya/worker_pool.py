"""Bounded Laya workers with explicit completion, error, and cache accounting."""
import asyncio
from collections import deque
import json
import logging
import sqlite3
import time
from .analyzer import LayaSEOAnalyzer
from .decision import LayaDecision, LAYA_PROMPT_VERSION, load_settings
from .heads import LayaHeadMissingError
from .persistence import JSON_COLUMNS, insert_decision

logger = logging.getLogger("seojev.laya.worker_pool")


class LayaCacheError(RuntimeError):
    pass


class LayaWorkerPool:
    def __init__(self, model_id="aac6fef/laya-mlx", max_queue_depth=5000, num_workers=2,
                 batch_size=10, decision_callback=None, cache_db_path=None, settings=None):
        self.settings = {**load_settings(), **(settings or {})}
        self.model_id, self.max_queue_depth = model_id, max_queue_depth
        self.num_workers, self.batch_size = num_workers, batch_size
        self.decision_callback, self.cache_db_path = decision_callback, cache_db_path
        self._queue = asyncio.Queue(maxsize=max_queue_depth)
        self._decisions, self._workers = [], []
        self._analyzer = None
        self.total_candidates = self.total_decisions = self.total_errors = 0
        self.total_cache_hits = self.total_cache_misses = self.queue_drops = 0
        self.persist_failures = self.cache_read_failures = self.fatal_errors = 0
        self.recent_errors = deque(maxlen=self.settings["max_recent_errors"])
        self._latencies = deque(maxlen=1000)
        self._started_at = 0
        if num_workers < 1 or max_queue_depth < 1 or not 0 <= self.settings["max_error_rate"] <= 1:
            raise ValueError("Invalid Laya worker configuration")

    async def start(self):
        self._analyzer = LayaSEOAnalyzer.get_singleton(self.model_id)
        self._analyzer.preflight()  # Fail before submitting any candidates.
        self._started_at = time.monotonic()
        self._workers = [asyncio.create_task(self._worker_loop(i)) for i in range(self.num_workers)]

    async def submit_candidate(self, candidate, run_id=""):
        try:
            self._queue.put_nowait((candidate, run_id))
        except asyncio.QueueFull:
            self.queue_drops += 1
            logger.error("Laya queue rejected candidate %s", candidate.cluster_id)
            return False
        self.total_candidates += 1
        return True

    async def finish(self):
        try:
            await asyncio.wait_for(self._queue.join(), timeout=self.settings["queue_timeout_seconds"])
        except asyncio.TimeoutError as exc:
            self.recent_errors.append("Laya queue timeout: not all submitted candidates completed")
            self.fatal_errors += 1
            raise RuntimeError(f"Laya pass incomplete: {self.get_metrics()}") from exc
        summary = self.get_metrics()
        if (not self.total_decisions or self.queue_drops or self.fatal_errors
                or self.total_decisions + self.total_errors != self.total_candidates
                or summary["error_rate"] > self.settings["max_error_rate"]):
            raise RuntimeError(f"Laya pass failed completion/error checks: {summary}")
        return list(self._decisions)

    async def stop(self, abort=False):
        try:
            if not abort and (self._queue.qsize() or self.total_candidates > self.total_decisions + self.total_errors):
                await self.finish()
        finally:
            for task in self._workers:
                task.cancel()
            results = await asyncio.gather(*self._workers, return_exceptions=True)
            for result in results:
                if isinstance(result, BaseException) and not isinstance(result, asyncio.CancelledError):
                    raise RuntimeError("Laya worker task exited unexpectedly") from result
        logger.info("Laya worker summary: %s", self.get_metrics())

    async def get_decisions(self):
        return list(self._decisions)

    def get_metrics(self):
        latencies = sorted(self._latencies) or [0]
        return {"total_candidates": self.total_candidates, "total_decisions": self.total_decisions,
                "total_cache_hits": self.total_cache_hits, "total_cache_misses": self.total_cache_misses,
                "inference_count": self.total_cache_misses, "total_errors": self.total_errors,
                "persist_failures": self.persist_failures, "cache_read_failures": self.cache_read_failures,
                "fatal_errors": self.fatal_errors, "recent_errors": list(self.recent_errors),
                "error_rate": self.total_errors / max(self.total_candidates, 1),
                "queue_drops": self.queue_drops, "queue_depth": self._queue.qsize(),
                "p50_ms": latencies[len(latencies)//2], "p95_ms": latencies[int((len(latencies)-1)*.95)],
                "p99_ms": latencies[int((len(latencies)-1)*.99)],
                "decisions_per_sec": self.total_decisions / max(time.monotonic()-self._started_at, .001) if self._started_at else 0}

    async def _worker_loop(self, worker_id):
        while True:
            candidate, run_id = await self._queue.get()
            try:
                decision = await asyncio.to_thread(self._make_decision, candidate, run_id)
                self._persist_decision(decision)
                if self.decision_callback:
                    self.decision_callback(decision)
                self._decisions.append(decision)
                self.total_decisions += 1
                self.total_cache_hits += int(decision.from_cache)
                self.total_cache_misses += int(not decision.from_cache)
                self._latencies.append(decision.latency_ms)
            except Exception as exc:
                self.total_errors += 1
                self.fatal_errors += int(isinstance(exc, (LayaHeadMissingError, LayaCacheError)))
                self.recent_errors.append(f"{candidate.cluster_id}: {type(exc).__name__}: {exc}")
                logger.exception("Laya worker %s failed candidate %s", worker_id, candidate.cluster_id)
            finally:
                # Completion means inference AND persistence finished, never just dequeue.
                self._queue.task_done()

    def _make_decision(self, candidate, run_id):
        checkpoint = self._analyzer.get_backend().checkpoint_id
        input_hash = candidate.compute_hash(checkpoint)
        cached = self._load_cached_decision(input_hash)
        if cached is not None:
            cached.run_id, cached.cluster_id, cached.from_cache = run_id, candidate.cluster_id, True
            return cached
        issue_data = {"cluster_id": candidate.cluster_id, "issue": candidate.issue_type,
                      "category": candidate.category_hint, "severity": candidate.severity_hint,
                      "template": candidate.template_id, "affected_urls_count": candidate.page_count,
                      "status_distribution": candidate.status_distribution,
                      "canonical_indexability": candidate.canonical_relationship or candidate.indexability,
                      "content_metrics": candidate.content_metrics, "link_metrics": candidate.link_metrics,
                      "query_metrics": candidate.query_metrics, "schema_metrics": candidate.schema_metrics,
                      "evidence_refs": candidate.evidence_refs, "root_cause": candidate.issue_type}
        result = self._analyzer.classify_issue(issue_data, run_id)
        return LayaDecision(decision_id=f"dec_{input_hash}", run_id=run_id, cluster_id=candidate.cluster_id,
                            decision_type="SEO_PROBLEM" if result["is_real_issue"] else "NO_SEO_PROBLEM",
                            head_confidences=result["head_confidences"], checkpoint_id=checkpoint,
                            policy=self.settings["confidence"], reason_codes=[result["category"]],
                            recommended_action=result["action"], affected_scope=result["scope"],
                            affected_count=candidate.page_count, evidence_refs=candidate.evidence_refs,
                            model_version=self.model_id, input_hash=input_hash, latency_ms=result["latency_ms"],
                            raw_response=result["raw_response"], from_cache=result["from_cache"],
                            canonical_indexability=result["canonical_indexability"], content_assessment=result["content_assessment"],
                            cannibalization=result["cannibalization"], internal_linking=result["internal_linking"])

    def _load_cached_decision(self, input_hash):
        if not self.cache_db_path:
            return None
        try:
            with sqlite3.connect(self.cache_db_path, timeout=30) as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute("SELECT * FROM laya_decision_log WHERE input_hash=? AND model_version=? AND checkpoint_id=? AND prompt_version=?", (input_hash, self.model_id, self._analyzer.get_backend().checkpoint_id, LAYA_PROMPT_VERSION)).fetchone()
            if row is None:
                return None
            data = dict(row)
            for column in JSON_COLUMNS:
                data[column] = json.loads(data[column])
            data["policy"] = self.settings["confidence"]
            return LayaDecision.from_dict(data)
        except (sqlite3.Error, ValueError, TypeError) as exc:
            self.cache_read_failures += 1
            logger.exception("Laya cache read failed")
            raise LayaCacheError(f"Cannot read Laya cache: {exc}") from exc

    def _persist_decision(self, decision):
        if not self.cache_db_path:
            return
        try:
            with sqlite3.connect(self.cache_db_path, timeout=30) as conn:
                if insert_decision(conn, "laya_decision_log", decision) != 1:
                    raise sqlite3.IntegrityError("Laya cache insert did not write one row")
        except sqlite3.Error as exc:
            self.persist_failures += 1
            logger.exception("Laya cache persistence failed")
            raise LayaCacheError(f"Cannot persist Laya decision: {exc}") from exc
