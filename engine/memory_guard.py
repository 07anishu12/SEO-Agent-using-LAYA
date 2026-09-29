"""Bounded work with current RSS, available-memory and swap-growth stop signals."""
from contextlib import contextmanager
import gc
import json
import logging
import os
import time
import psutil

log = logging.getLogger(__name__)


class MemoryBudgetExceeded(RuntimeError):
    pass


class MemoryGuard:
    def __init__(self, limit_mb=4096, check_interval_sec=0, *, batch_size=8,
                 min_available_mb=1536, pause_seconds=2, max_swap_delta_mb=64.0, sample=None, sleep=time.sleep):
        self.limit_mb = float(os.getenv('SEOJEV_MEMORY_BUDGET_MB', limit_mb))
        self.batch_size = batch_size
        self.min_available_mb = float(os.getenv('SEOJEV_MIN_AVAILABLE_MB', min_available_mb))
        self.pause_seconds, self.sleep = pause_seconds, sleep
        self.max_swap_delta_mb = float(os.getenv('SEOJEV_MAX_SWAP_DELTA_MB', max_swap_delta_mb))
        self.sample = sample or self._sample
        self.peak_rss_mb = 0.0
        self.stages = {}
        self.active_stage = None
        self.initial = self.sample()
        self.peak_rss_mb = self.initial['rss_mb']
        self.inference_initial = None

    def rebase_inference(self):
        """Establish post-model-load baseline for inference-stage swap and pageout safety."""
        self.inference_initial = self.sample()

    @staticmethod
    def _sample():
        process = psutil.Process()
        rss = process.memory_info().rss
        for child in process.children(recursive=True):
            try:
                rss += child.memory_info().rss
            except psutil.NoSuchProcess:
                pass
        swap = psutil.swap_memory()
        return dict(rss_mb=rss / 2**20, available_mb=psutil.virtual_memory().available / 2**20,
                    swap_used=swap.used, swap_out=swap.sout)

    def get_current_rss_mb(self):
        return self.sample()['rss_mb']

    def observe(self):
        state = self.sample()
        self.peak_rss_mb = max(self.peak_rss_mb, state['rss_mb'])
        if self.active_stage:
            record = self.stages[self.active_stage]
            record['peak_rss_mb'] = max(record['peak_rss_mb'], state['rss_mb'])
        # Monitor actual swap growth against configured threshold (default 64MB)
        swap_delta_bytes = state['swap_used'] - self.initial['swap_used']
        swap_delta_mb = swap_delta_bytes / (1024 * 1024)
        if swap_delta_mb > self.max_swap_delta_mb:
            raise MemoryBudgetExceeded(
                f'System swap grew by {swap_delta_mb:.1f} MiB (threshold {self.max_swap_delta_mb:.1f} MiB); '
                'aborting safely before memory exhaustion. Close other applications or run this checkpoint on a larger host.'
            )
        return state

    def over_budget(self, state, reserve_mb=0):
        return state['rss_mb'] + reserve_mb > self.limit_mb or state['available_mb'] < self.min_available_mb + reserve_mb

    def checkpoint(self, reserve_mb=0):
        state = self.observe()
        if not self.over_budget(state, reserve_mb):
            return self.batch_size
        self.batch_size = max(1, self.batch_size // 2)
        gc.collect()
        state = self.observe()
        if not self.over_budget(state, reserve_mb):
            return self.batch_size
        self.sleep(self.pause_seconds)  # Exactly one pause, never an unbounded retry loop.
        state = self.observe()
        if self.over_budget(state, reserve_mb):
            raise MemoryBudgetExceeded(f'Memory pressure persists after batch shrink and pause: RSS={state["rss_mb"]:.1f} MiB, budget={self.limit_mb:.1f} MiB, available={state["available_mb"]:.1f} MiB. Aborted safely; resume the saved chunk on a larger host.')
        return self.batch_size

    def check_and_enforce(self, raise_on_exceeded: bool = True):
        try:
            self.checkpoint()
            return True
        except MemoryBudgetExceeded:
            if raise_on_exceeded:
                raise
            return False

    @contextmanager
    def stage(self, name):
        previous = self.active_stage
        self.active_stage = name
        self.stages.setdefault(name, dict(seconds=0., peak_rss_mb=0.))
        start = time.monotonic()
        try:
            self.checkpoint()
            yield
            self.checkpoint()
        finally:
            self.stages[name]['seconds'] += time.monotonic() - start
            log.info('stage=%s %s', name, self.stages[name])
            self.active_stage = previous


def autotune_batches(measure_batch, guard, output, contract):
    """Measure actual submitted chunks, not extrapolated allocation; scalar MLX stays scalar."""
    measurements, safe = [], 0
    for size in (8, 16, 32, 64):
        try:
            guard.checkpoint()
            before = guard.peak_rss_mb
            start = time.monotonic()
            measure_batch(size)
            guard.checkpoint()
            measurements.append(dict(batch_size=size, peak_rss_mb=guard.peak_rss_mb,
                                     previous_peak_mb=before, seconds=time.monotonic()-start))
            safe = size
        except MemoryBudgetExceeded as exc:
            measurements.append(dict(batch_size=size, error=str(exc)))
            break
    result = dict(safe_batch_size=safe, contract=contract, measurements=measurements,
                  meaning='Maximum measured safe submission chunk; current checkpoint API predicts one candidate at a time')
    from pathlib import Path
    Path(output).write_text(json.dumps(result, indent=2))
    return result
