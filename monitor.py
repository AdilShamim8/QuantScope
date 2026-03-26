"""
Monitoring module.

Tracks system health metrics that matter:
1. API latency per request
2. Yahoo Finance API reliability
3. LLM provider availability and latency
4. Cache hit rate
5. Validation rejection rate

This is Phase 6 of the production framework.
Without monitoring, failures are silent.
"""

import logging
import time
from collections import defaultdict
from datetime import datetime
from threading import Lock

logger = logging.getLogger(__name__)


class Metrics:
    """
    Thread-safe in-memory metrics collector.

    Stores:
      - counters (event totals)
      - timings (duration samples in seconds)
    """

    def __init__(self):
        # Lock keeps updates safe when multiple requests run in parallel.
        self._lock = Lock()
        # Named counters for simple totals (e.g., analyses_completed).
        self._counters = defaultdict(int)
        # Named timing buckets storing recent duration samples.
        self._timings = defaultdict(list)
        # Start time used to compute process uptime in snapshots.
        self._start = datetime.now()

    def count(self, name, n=1):
        """Increment named counter by n (default 1)."""
        with self._lock:
            self._counters[name] += n

    def time(self, name, seconds):
        """Record one timing sample (seconds) under metric name."""
        with self._lock:
            self._timings[name].append(seconds)
            # Keep only last 1000 measurements
            if len(self._timings[name]) > 1000:
                self._timings[name] = self._timings[name][-1000:]

    def snapshot(self):
        """Return a summary payload suitable for health/debug endpoints."""
        with self._lock:
            # Base snapshot includes uptime and raw counters.
            result = {
                "uptime_seconds": (datetime.now() - self._start).total_seconds(),
                "counters": dict(self._counters),
                "timings": {},
            }

            # Convert timing samples into aggregate stats (count/mean/max/min).
            for name, values in self._timings.items():
                if values:
                    result["timings"][name] = {
                        "count": len(values),
                        "mean_ms": round(sum(values) / len(values) * 1000, 1),
                        "max_ms": round(max(values) * 1000, 1),
                        "min_ms": round(min(values) * 1000, 1),
                    }
            return result


# Global singleton used across API/pipeline modules.
metrics = Metrics()