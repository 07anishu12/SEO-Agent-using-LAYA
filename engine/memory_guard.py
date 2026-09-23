import gc
import os
import resource
import time
from typing import Optional

class MemoryGuard:
    """Monitors process RSS and triggers garbage collection to enforce configurable ceiling."""
    def __init__(self, limit_mb: float = 2048.0, check_interval_sec: float = 10.0):
        self.limit_mb = limit_mb
        self.warning_threshold_mb = limit_mb * 0.8 # 80% ceiling
        self.check_interval_sec = check_interval_sec
        self.last_check_time = 0.0
        self.peak_rss_mb = 0.0

    def get_current_rss_mb(self) -> float:
        """Returns current process Resident Set Size (RSS) in Megabytes."""
        # 1. Try querying OS for actual live dynamic RSS
        try:
            import subprocess
            out = subprocess.check_output(["ps", "-o", "rss=", "-p", str(os.getpid())], timeout=0.5)
            rss_kb = int(out.strip())
            rss_mb = rss_kb / 1024.0
            if rss_mb > self.peak_rss_mb:
                self.peak_rss_mb = rss_mb
            return rss_mb
        except Exception:
            pass

        # 2. Fallback to resource.getrusage (historical peak)
        try:
            usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            if os.uname().sysname == "Darwin":
                rss_mb = usage / (1024.0 * 1024.0)
            else:
                rss_mb = usage / 1024.0
            if rss_mb > self.peak_rss_mb:
                self.peak_rss_mb = rss_mb
            return rss_mb
        except Exception:
            return 0.0

    def check_and_enforce(self) -> bool:
        """Checks memory consumption. If above warning threshold, triggers gc.collect().
        Returns True if memory is within bounds, False if exceeding limit.
        """
        now = time.monotonic()
        if now - self.last_check_time < self.check_interval_sec:
            return True

        self.last_check_time = now
        current_rss = self.get_current_rss_mb()

        if current_rss >= self.warning_threshold_mb:
            gc.collect()
            current_rss = self.get_current_rss_mb()

        return current_rss <= self.limit_mb
