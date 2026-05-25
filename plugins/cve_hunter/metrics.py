"""CVE Hunter Metrics.

Metrics collection for dashboard and observability.
Integrates with core observability stack.
"""

from core.observability.logging import get_logger
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from collections import defaultdict

logger = get_logger(__name__)


# =============================================================================
# Metric Types
# =============================================================================


@dataclass
class MetricPoint:
    """A single metric data point."""

    name: str
    value: float
    timestamp: datetime
    labels: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict."""
        return {
            "name": self.name,
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "labels": self.labels,
        }


@dataclass
class MetricSeries:
    """A time series of metrics."""

    name: str
    points: List[MetricPoint] = field(default_factory=list)
    max_points: int = 1000

    def add(self, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Add a point to the series."""
        point = MetricPoint(
            name=self.name,
            value=value,
            timestamp=datetime.now(timezone.utc),
            labels=labels or {},
        )
        self.points.append(point)
        if len(self.points) > self.max_points:
            self.points = self.points[-self.max_points :]

    def get_latest(self) -> Optional[MetricPoint]:
        """Get most recent point."""
        return self.points[-1] if self.points else None

    def get_average(self, n: int = 10) -> float:
        """Get rolling average of last n points."""
        recent = self.points[-n:] if self.points else []
        if not recent:
            return 0.0
        return sum(p.value for p in recent) / len(recent)


# =============================================================================
# CVE Hunter Metrics
# =============================================================================


class CVEHunterMetrics:
    """Metrics collector for CVE Hunter plugin.

    Tracks scan performance, CVE discovery rates, and agent health.

    Example:
        ```python
        metrics = CVEHunterMetrics()
        metrics.record_scan("nvd", duration=5.2, cves_found=10)
        stats = metrics.get_dashboard_stats()
        ```
    """

    def __init__(self):
        """Initialize metrics collector."""
        self._counters: Dict[str, int] = defaultdict(int)
        self._gauges: Dict[str, float] = {}
        self._series: Dict[str, MetricSeries] = {}
        self._start_time = datetime.now(timezone.utc)

        # Initialize core metrics
        self._init_metrics()

    def _init_metrics(self) -> None:
        """Initialize default metric series."""
        series_names = [
            "scan_duration_seconds",
            "cves_found_per_scan",
            "analysis_duration_seconds",
            "discovery_confidence",
            "alert_count",
            "memory_usage_mb",
        ]
        for name in series_names:
            self._series[name] = MetricSeries(name=name)

    # =========================================================================
    # Recording Methods
    # =========================================================================

    def record_scan(
        self,
        source: str,
        duration: float,
        cves_found: int,
        new_cves: int = 0,
        errors: int = 0,
    ) -> None:
        """Record a scan completion.

        Args:
            source: Data source scanned
            duration: Scan duration in seconds
            cves_found: Total CVEs found
            new_cves: New CVEs discovered
            errors: Errors encountered
        """
        labels = {"source": source}

        self._series["scan_duration_seconds"].add(duration, labels)
        self._series["cves_found_per_scan"].add(cves_found, labels)

        self._counters["scans_total"] += 1
        self._counters[f"scans_{source}"] += 1
        self._counters["cves_found_total"] += cves_found
        self._counters["cves_new_total"] += new_cves
        self._counters["scan_errors_total"] += errors

        self._gauges["last_scan_duration"] = duration
        self._gauges["last_scan_cves"] = cves_found

        logger.debug(
            f"Recorded scan: source={source}, duration={duration:.2f}s, cves={cves_found}"
        )

    def record_analysis(
        self,
        cve_id: str,
        duration: float,
        success: bool,
        corrections: int = 0,
    ) -> None:
        """Record an analysis completion.

        Args:
            cve_id: CVE analyzed
            duration: Analysis duration
            success: Whether analysis succeeded
            corrections: Self-corrections made
        """
        self._series["analysis_duration_seconds"].add(duration, {"cve_id": cve_id})

        self._counters["analyses_total"] += 1
        if success:
            self._counters["analyses_success"] += 1
        else:
            self._counters["analyses_failed"] += 1
        self._counters["corrections_total"] += corrections

    def record_discovery(
        self,
        pattern: str,
        confidence: float,
        confirmed: bool = False,
    ) -> None:
        """Record a discovery.

        Args:
            pattern: Pattern detected
            confidence: Confidence score
            confirmed: Whether discovery was confirmed
        """
        self._series["discovery_confidence"].add(confidence, {"pattern": pattern})

        self._counters["discoveries_total"] += 1
        if confirmed:
            self._counters["discoveries_confirmed"] += 1

    def record_alert(self, severity: str) -> None:
        """Record an alert creation.

        Args:
            severity: Alert severity level
        """
        self._counters["alerts_total"] += 1
        self._counters[f"alerts_{severity}"] += 1
        self._series["alert_count"].add(1, {"severity": severity})

    def record_correlation(self, correlation_type: str, cve_count: int) -> None:
        """Record a correlation finding.

        Args:
            correlation_type: Type of correlation
            cve_count: Number of CVEs in correlation
        """
        self._counters["correlations_total"] += 1
        self._counters[f"correlations_{correlation_type}"] += 1
        self._gauges["last_correlation_size"] = cve_count

    # =========================================================================
    # Gauge Updates
    # =========================================================================

    def set_active_agents(self, count: int) -> None:
        """Set number of active agents."""
        self._gauges["active_agents"] = count

    def set_memory_usage(self, mb: float) -> None:
        """Set memory usage in MB."""
        self._gauges["memory_usage_mb"] = mb
        self._series["memory_usage_mb"].add(mb)

    def set_cve_cache_size(self, count: int) -> None:
        """Set CVE cache size."""
        self._gauges["cve_cache_size"] = count

    # =========================================================================
    # Query Methods
    # =========================================================================

    def get_counter(self, name: str) -> int:
        """Get a counter value."""
        return self._counters.get(name, 0)

    def get_gauge(self, name: str) -> float:
        """Get a gauge value."""
        return self._gauges.get(name, 0.0)

    def get_series(self, name: str) -> Optional[MetricSeries]:
        """Get a metric series."""
        return self._series.get(name)

    def get_dashboard_stats(self) -> Dict[str, Any]:
        """Get stats for dashboard display.

        Returns:
            Dict with all dashboard metrics
        """
        uptime = (datetime.now(timezone.utc) - self._start_time).total_seconds()

        return {
            "uptime_seconds": uptime,
            "scans": {
                "total": self._counters["scans_total"],
                "last_duration": self._gauges.get("last_scan_duration", 0),
                "avg_duration": self._series["scan_duration_seconds"].get_average(),
            },
            "cves": {
                "total_found": self._counters["cves_found_total"],
                "new_discovered": self._counters["cves_new_total"],
                "cache_size": self._gauges.get("cve_cache_size", 0),
            },
            "analysis": {
                "total": self._counters["analyses_total"],
                "success_rate": (
                    self._counters["analyses_success"]
                    / max(1, self._counters["analyses_total"])
                )
                * 100,
                "corrections": self._counters["corrections_total"],
            },
            "discoveries": {
                "total": self._counters["discoveries_total"],
                "confirmed": self._counters["discoveries_confirmed"],
                "avg_confidence": self._series["discovery_confidence"].get_average(),
            },
            "alerts": {
                "total": self._counters["alerts_total"],
                "critical": self._counters["alerts_critical"],
                "high": self._counters["alerts_high"],
            },
            "correlations": {
                "total": self._counters["correlations_total"],
            },
            "health": {
                "active_agents": self._gauges.get("active_agents", 0),
                "memory_mb": self._gauges.get("memory_usage_mb", 0),
            },
        }

    def export_prometheus(self) -> str:
        """Export metrics in Prometheus format.

        Returns:
            Prometheus-formatted metrics string
        """
        lines = ["# CVE Hunter Metrics"]

        # Counters
        for name, value in self._counters.items():
            lines.append(f"cve_hunter_{name} {value}")

        # Gauges
        for name, value in self._gauges.items():
            lines.append(f"cve_hunter_{name} {value}")

        return "\n".join(lines)


# =============================================================================
# Singleton
# =============================================================================

_metrics_instance: Optional[CVEHunterMetrics] = None


def get_cve_hunter_metrics() -> CVEHunterMetrics:
    """Get singleton metrics instance."""
    global _metrics_instance
    if _metrics_instance is None:
        _metrics_instance = CVEHunterMetrics()
    return _metrics_instance
