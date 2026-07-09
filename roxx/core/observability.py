"""Small dependency-free metrics registry for the RoXX HTTP service."""

from __future__ import annotations

import threading
import time
from collections import Counter

import psutil


class RequestMetrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._started_at = time.monotonic()
        self._requests: Counter[tuple[str, str, int]] = Counter()
        self._duration_seconds: Counter[tuple[str, str]] = Counter()

    def observe(self, method: str, route: str, status: int, duration_seconds: float) -> None:
        with self._lock:
            self._requests[(method, route, status)] += 1
            self._duration_seconds[(method, route)] += duration_seconds

    @staticmethod
    def _labels(method: str, route: str, status: int | None = None) -> str:
        escaped_route = route.replace("\\", "\\\\").replace('"', '\\"')
        labels = f'method="{method}",route="{escaped_route}"'
        if status is not None:
            labels += f',status="{status}"'
        return "{" + labels + "}"

    def render_prometheus(self) -> str:
        process = psutil.Process()
        with self._lock:
            requests = list(self._requests.items())
            durations = list(self._duration_seconds.items())
            uptime = time.monotonic() - self._started_at

        lines = [
            "# HELP roxx_up Whether the RoXX process is serving metrics.",
            "# TYPE roxx_up gauge",
            "roxx_up 1",
            "# HELP roxx_process_uptime_seconds Process uptime in seconds.",
            "# TYPE roxx_process_uptime_seconds gauge",
            f"roxx_process_uptime_seconds {uptime:.3f}",
            "# HELP roxx_process_resident_memory_bytes Resident process memory.",
            "# TYPE roxx_process_resident_memory_bytes gauge",
            f"roxx_process_resident_memory_bytes {process.memory_info().rss}",
            "# HELP roxx_http_requests_total HTTP requests handled by route.",
            "# TYPE roxx_http_requests_total counter",
        ]
        for (method, route, status), count in sorted(requests):
            lines.append(
                f"roxx_http_requests_total{self._labels(method, route, status)} {count}"
            )
        lines.extend(
            [
                "# HELP roxx_http_request_duration_seconds_total Total HTTP request duration.",
                "# TYPE roxx_http_request_duration_seconds_total counter",
            ]
        )
        for (method, route), duration in sorted(durations):
            lines.append(
                "roxx_http_request_duration_seconds_total"
                f"{self._labels(method, route)} {duration:.6f}"
            )
        return "\n".join(lines) + "\n"


request_metrics = RequestMetrics()
