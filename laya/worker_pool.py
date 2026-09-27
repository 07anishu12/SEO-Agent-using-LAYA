"""Laya Decision Worker Pool — Isolated from crawler, with backpressure and batching."""
import asyncio
import logging
import time
import json
import sqlite3
import os
from collections import deque
from typing import Dict, Any, List, Optional, Callable

from .analyzer import LayaSEOAnalyzer
from .decision import LayaDecision, LayaCandidateInput, DecisionType, ConfidenceGate, LAYA_PROMPT_VERSION

logger = logging.getLogger("seojev.laya.worker_pool")


class LayaWorkerPool:
    """Manages a bounded queue of Laya candidates and processes them asynchronously.
    
    Fully isolated from the crawler — crawler never waits for Laya.
    Uses backpressure: if queue exceeds max_depth, new candidates are dropped with warning.
    """

    def __init__(
        self,
        model_id: str = "aac6fef/laya-mlx",
        max_queue_depth: int = 5000,
        num_workers: int = 2,
        batch_size: int = 10,
        decision_callback: Optional[Callable[[LayaDecision], None]] = None
        , cache_db_path: Optional[str] = None
    ):
        self.model_id = model_id
        self.max_queue_depth = max_queue_depth
        self.num_workers = num_workers
        self.batch_size = batch_size
        self.decision_callback = decision_callback
        self.cache_db_path = cache_db_path
        
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_depth)
        self._decisions: List[LayaDecision] = []
        self._decisions_lock = asyncio.Lock()
        self._workers: List[asyncio.Task] = []
        self._shutdown = asyncio.Event()
        self._analyzer: Optional[LayaSEOAnalyzer] = None
        
        # Metrics
        self.total_candidates = 0
        self.total_decisions = 0
        self.total_cache_hits = 0
        self.total_cache_misses = 0
        self.total_errors = 0
        self.queue_drops = 0
        self._latencies: deque = deque(maxlen=1000)
        self._started_at = 0.0

    async def start(self):
        """Start worker pool and warm up the model."""
        self._analyzer = LayaSEOAnalyzer.get_singleton(model_id=self.model_id)
        self._started_at = time.monotonic()
        # Warm the backend
        try:
            self._analyzer.get_backend()
            logger.info(f"Laya worker pool started: {self.num_workers} workers, queue_max={self.max_queue_depth}")
        except Exception as e:
            logger.warning(f"Laya backend warmup failed (will use fallback): {e}")
        
        self._workers = [
            asyncio.create_task(self._worker_loop(i))
            for i in range(self.num_workers)
        ]

    async def stop(self):
        """Gracefully drain queue and stop workers."""
        self._shutdown.set()
        # Wait for queue to drain
        try:
            await asyncio.wait_for(self._queue.join(), timeout=30.0)
        except asyncio.TimeoutError:
            logger.warning("Laya queue drain timed out after 30s")
        # Cancel workers
        for w in self._workers:
            w.cancel()
        await asyncio.gather(*self._workers, return_exceptions=True)
        logger.info(f"Laya worker pool stopped: {self.total_decisions} decisions, {self.total_cache_hits} cache hits")

    async def submit_candidate(self, candidate: LayaCandidateInput, run_id: str = "") -> bool:
        """Submit a candidate for Laya decision. Returns False if queue is full (backpressure)."""
        try:
            self._queue.put_nowait((candidate, run_id))
            self.total_candidates += 1
            return True
        except asyncio.QueueFull:
            self.queue_drops += 1
            logger.warning(f"Laya queue full ({self.max_queue_depth}), dropping candidate {candidate.cluster_id}")
            return False

    async def get_decisions(self) -> List[LayaDecision]:
        """Get all completed decisions."""
        async with self._decisions_lock:
            decisions = list(self._decisions)
            return decisions

    def get_metrics(self) -> Dict[str, Any]:
        """Return worker pool performance metrics."""
        latencies = list(self._latencies)
        sorted_lat = sorted(latencies) if latencies else [0]
        return {
            "total_candidates": self.total_candidates,
            "total_decisions": self.total_decisions,
            "total_cache_hits": self.total_cache_hits,
            "total_cache_misses": self.total_cache_misses,
            "total_errors": self.total_errors,
            "queue_drops": self.queue_drops,
            "queue_depth": self._queue.qsize(),
            "p50_ms": sorted_lat[len(sorted_lat) // 2] if sorted_lat else 0,
            "p95_ms": sorted_lat[int(len(sorted_lat) * 0.95)] if len(sorted_lat) > 1 else 0,
            "p99_ms": sorted_lat[int(len(sorted_lat) * 0.99)] if len(sorted_lat) > 1 else 0,
            "decisions_per_sec": round(self.total_decisions / max(time.monotonic() - self._started_at, 0.001), 3) if self._started_at else 0.0,
        }

    async def _worker_loop(self, worker_id: int):
        """Worker loop: dequeues candidates and processes them."""
        while not self._shutdown.is_set() or not self._queue.empty():
            try:
                # Batch collection with timeout
                batch = []
                try:
                    item = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                    batch.append(item)
                except asyncio.TimeoutError:
                    continue
                
                # Try to collect more items up to batch_size
                while len(batch) < self.batch_size:
                    try:
                        item = self._queue.get_nowait()
                        batch.append(item)
                    except asyncio.QueueEmpty:
                        break
                
                # Process batch
                for candidate, run_id in batch:
                    try:
                        decision = await asyncio.to_thread(
                            self._make_decision, candidate, run_id
                        )
                        async with self._decisions_lock:
                            self._decisions.append(decision)
                        self.total_decisions += 1
                        if decision.from_cache:
                            self.total_cache_hits += 1
                        else:
                            self.total_cache_misses += 1
                        self._latencies.append(decision.latency_ms)
                        self._persist_decision(decision)
                        
                        if self.decision_callback:
                            try:
                                self.decision_callback(decision)
                            except Exception:
                                pass
                    except Exception as e:
                        self.total_errors += 1
                        logger.error(f"Laya worker {worker_id} error: {e}")
                    finally:
                        self._queue.task_done()
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Laya worker {worker_id} unexpected error: {e}")
                await asyncio.sleep(0.1)

    def _make_decision(self, candidate: LayaCandidateInput, run_id: str) -> LayaDecision:
        """Synchronous decision-making using LayaSEOAnalyzer."""
        input_hash = candidate.compute_hash(self._analyzer.model_id)
        cached = self._load_cached_decision(input_hash)
        if cached:
            cached.run_id = run_id
            cached.from_cache = True
            return cached

        issue_data = {
            "cluster_id": candidate.cluster_id,
            "issue": candidate.issue_type,
            "category": candidate.category_hint,
            "severity": candidate.severity_hint,
            "template": candidate.template_id,
            "affected_urls_count": candidate.page_count,
            "evidence": json.dumps({
                "status_distribution": candidate.status_distribution,
                "content_metrics": candidate.content_metrics,
                "page_count": candidate.page_count,
            }, default=str)[:150]
        }
        issue_data.update({
            "canonical_indexability": candidate.canonical_relationship or candidate.indexability,
            "content_metrics": candidate.content_metrics,
            "link_metrics": candidate.link_metrics,
            "query_metrics": candidate.query_metrics,
            "schema_metrics": candidate.schema_metrics,
            "evidence_refs": candidate.evidence_refs,
            "root_cause": candidate.issue_type,
        })
        
        result = self._analyzer.classify_issue(issue_data, run_id=run_id)
        
        
        # Map legacy result to LayaDecision
        decision_type = self._infer_decision_type(candidate.issue_type, result.get("action", ""))
        
        return LayaDecision(
            decision_id=result.get("decision_id", f"dec_{input_hash[:16]}"),
            run_id=run_id,
            cluster_id=candidate.cluster_id,
            decision_type=decision_type,
            choice=result.get("action", "investigate"),
            is_real_issue=bool(result.get("is_real_issue", result.get("verdict", "real_issue") not in {"noise", "no_issue"})),
            confidence=result.get("confidence", 0.5),
            severity=result.get("severity", candidate.severity_hint),
            scope=result.get("scope", "template" if candidate.page_count > 1 else "page"),
            root_cause=result.get("root_cause", candidate.issue_type),
            canonical_indexability=result.get("canonical_indexability", candidate.canonical_relationship or candidate.indexability),
            content_assessment=result.get("content_assessment", candidate.content_metrics),
            cannibalization=result.get("cannibalization", {}),
            internal_linking=result.get("internal_linking", candidate.link_metrics),
            reason_codes=[result.get("category", "technical")],
            recommended_action=result.get("action", "investigate"),
            affected_scope=candidate.template_id if candidate.page_count > 1 else "page",
            affected_count=candidate.page_count,
            evidence_refs=candidate.evidence_refs,
            model_version=self._analyzer.model_id,
            input_hash=input_hash,
            latency_ms=result.get("latency_ms", 0.0),
            from_cache=result.get("from_cache", False),
            raw_response=result.get("raw_response", "")
        )

    def _load_cached_decision(self, input_hash: str) -> Optional[LayaDecision]:
        if not self.cache_db_path or not os.path.exists(self.cache_db_path):
            return None
        try:
            with sqlite3.connect(self.cache_db_path) as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute(
                    "SELECT * FROM laya_decision_log WHERE input_hash = ? AND model_version = ? AND prompt_version = ? ORDER BY created_at DESC LIMIT 1",
                    (input_hash, self.model_id, LAYA_PROMPT_VERSION),
                ).fetchone()
            if not row:
                return None
            return LayaDecision(
                decision_id=row["decision_id"], run_id=row["run_id"] or "", cluster_id=row["cluster_id"] or "",
                decision_type=row["decision_type"] or DecisionType.SEO_PROBLEM.value, choice=row["choice"] or "investigate",
                is_real_issue=bool(row["is_real_issue"] if "is_real_issue" in row.keys() else 1), confidence=row["confidence"] or 0.0,
                severity=row["severity"] or "medium", scope=row["scope"] if "scope" in row.keys() else "page",
                root_cause=row["root_cause"] if "root_cause" in row.keys() else "",
                canonical_indexability=json.loads(row["canonical_indexability"] or "{}") if "canonical_indexability" in row.keys() else {},
                content_assessment=json.loads(row["content_assessment"] or "{}") if "content_assessment" in row.keys() else {},
                cannibalization=json.loads(row["cannibalization"] or "{}") if "cannibalization" in row.keys() else {},
                internal_linking=json.loads(row["internal_linking"] or "{}") if "internal_linking" in row.keys() else {},
                reason_codes=json.loads(row["reason_codes"] or "[]"), evidence_refs=json.loads(row["evidence_refs"] or "[]"),
                model_version=row["model_version"] or self.model_id, input_hash=input_hash,
                latency_ms=row["latency_ms"] or 0.0, raw_response=row["raw_response"] or "", gate=row["gate"] or "HUMAN_REVIEW",
            )
        except (sqlite3.Error, ValueError, TypeError, json.JSONDecodeError):
            return None

    def _persist_decision(self, decision: LayaDecision):
        if not self.cache_db_path:
            return
        try:
            with sqlite3.connect(self.cache_db_path) as conn:
                conn.execute(
                    """INSERT OR REPLACE INTO laya_decision_log
                    (decision_id, run_id, cluster_id, decision_type, choice, confidence, severity, reason_codes,
                     recommended_action, affected_scope, affected_count, evidence_refs, model_version, input_hash,
                     latency_ms, created_at, from_cache, raw_response, gate, prompt_version, is_real_issue, scope,
                     root_cause, canonical_indexability, content_assessment, cannibalization, internal_linking)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (decision.decision_id, decision.run_id, decision.cluster_id, decision.decision_type, decision.choice,
                     decision.confidence, decision.severity, json.dumps(decision.reason_codes), decision.recommended_action,
                     decision.affected_scope, decision.affected_count, json.dumps(decision.evidence_refs), decision.model_version,
                     decision.input_hash, decision.latency_ms, decision.created_at, int(decision.from_cache), decision.raw_response,
                     decision.gate, LAYA_PROMPT_VERSION, int(decision.is_real_issue), decision.scope, decision.root_cause,
                     json.dumps(decision.canonical_indexability), json.dumps(decision.content_assessment),
                     json.dumps(decision.cannibalization), json.dumps(decision.internal_linking)),
                )
                conn.commit()
        except sqlite3.Error:
            logger.debug("Could not persist Laya decision cache", exc_info=True)

    @staticmethod
    def _infer_decision_type(issue_type: str, action: str) -> str:
        """Map issue_type + action to a bounded DecisionType."""
        issue_lower = issue_type.lower()
        if "canonical" in issue_lower:
            return DecisionType.CANONICAL_ACTION.value
        elif "redirect" in issue_lower:
            return DecisionType.REDIRECT_ACTION.value
        elif "duplicate" in issue_lower or "duplication" in issue_lower:
            return DecisionType.DUPLICATION.value
        elif "thin" in issue_lower:
            return DecisionType.THIN_CONTENT.value
        elif "cannibal" in issue_lower:
            return DecisionType.CANNIBALIZATION.value
        elif "index" in issue_lower:
            return DecisionType.NOINDEX.value if "noindex" in issue_lower else DecisionType.INDEX.value
        elif "content" in issue_lower:
            return DecisionType.CONTENT_ACTION.value
        elif "link" in issue_lower:
            return DecisionType.INTERNAL_LINK_ACTION.value
        elif "template" in issue_lower:
            return DecisionType.TEMPLATE_PROBLEM.value
        elif action == "no_action":
            return DecisionType.NO_SEO_PROBLEM.value
        else:
            return DecisionType.SEO_PROBLEM.value
