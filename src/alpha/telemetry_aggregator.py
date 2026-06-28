"""Telemetry aggregator — merges streams from vehicle, ground, and network sources.

Provides unified time-series view of all mission data.
Handles time synchronization, missing data, and rate conversion.
Pure math + data structures, zero external dependencies.
"""

import time
import math
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional


class SourceType(Enum):
    VEHICLE = auto()
    GROUND = auto()
    NETWORK = auto()
    SIMULATION = auto()


class MetricType(Enum):
    COUNTER = auto()
    GAUGE = auto()
    RATE = auto()
    HISTOGRAM = auto()


@dataclass
class TelemetryPoint:
    source: str
    metric: str
    value: float
    timestamp: float
    quality: int = 100
    metadata: dict = field(default_factory=dict)

    @property
    def age_ms(self) -> float:
        return (time.time() - self.timestamp) * 1000


@dataclass
class MetricDefinition:
    name: str
    metric_type: MetricType
    unit: str
    min_val: float = float("-inf")
    max_val: float = float("inf")
    decay_rate: float = 0.0


@dataclass
class AggregatedMetric:
    definition: MetricDefinition
    latest: float = 0.0
    count: int = 0
    sum: float = 0.0
    min_seen: float = float("inf")
    max_seen: float = float("-inf")
    last_update: float = 0.0

    @property
    def mean(self) -> float:
        return self.sum / self.count if self.count > 0 else 0.0

    @property
    def is_stale(self) -> bool:
        return (time.time() - self.last_update) > 10.0

    def update(self, value: float, timestamp: float):
        self.latest = value
        self.count += 1
        self.sum += value
        self.min_seen = min(self.min_seen, value)
        self.max_seen = max(self.max_seen, value)
        self.last_update = timestamp


class TelemetryAggregator:
    def __init__(self):
        self._metrics: dict[str, AggregatedMetric] = {}
        self._sources: dict[str, SourceType] = {}
        self._buffer: list[TelemetryPoint] = []
        self._max_buffer = 10000
        self._callbacks: list = []
        self._time_sync_offsets: dict[str, float] = {}
        self._rate_converters: dict[str, float] = {}

    def define_metric(self, definition: MetricDefinition):
        self._metrics[definition.name] = AggregatedMetric(definition=definition)

    def register_source(self, name: str, source_type: SourceType, clock_offset: float = 0.0):
        self._sources[name] = source_type
        self._time_sync_offsets[name] = clock_offset

    def set_rate(self, metric_name: str, target_rate_hz: float):
        self._rate_converters[metric_name] = 1.0 / target_rate_hz if target_rate_hz > 0 else 0

    def ingest(self, point: TelemetryPoint) -> bool:
        if point.source in self._time_sync_offsets:
            point.timestamp += self._time_sync_offsets[point.source]

        self._buffer.append(point)
        if len(self._buffer) > self._max_buffer:
            self._buffer = self._buffer[-self._max_buffer // 2:]

        metric = self._metrics.get(point.metric)
        if metric:
            metric.update(point.value, point.timestamp)

        for cb in self._callbacks:
            cb(point)

        return True

    def on_point(self, callback):
        self._callbacks.append(callback)

    def get_metric(self, name: str) -> Optional[AggregatedMetric]:
        return self._metrics.get(name)

    def query(
        self,
        metric: Optional[str] = None,
        source: Optional[str] = None,
        since: Optional[float] = None,
        limit: int = 100,
    ) -> list[TelemetryPoint]:
        results = []
        for p in reversed(self._buffer):
            if metric and p.metric != metric:
                continue
            if source and p.source != source:
                continue
            if since and p.timestamp < since:
                continue
            results.append(p)
            if len(results) >= limit:
                break
        return results

    def get_time_series(
        self, metric_name: str, duration_s: float = 60.0
    ) -> list[tuple[float, float]]:
        now = time.time()
        return [
            (p.timestamp, p.value)
            for p in self._buffer
            if p.metric == metric_name and p.timestamp >= now - duration_s
        ]

    def compute_derivative(self, metric_name: str, window_s: float = 5.0) -> float:
        ts = self.get_time_series(metric_name, window_s)
        if len(ts) < 2:
            return 0.0
        dt = ts[-1][0] - ts[0][0]
        if dt <= 0:
            return 0.0
        return (ts[-1][1] - ts[0][1]) / dt

    def compute_ema(self, metric_name: str, alpha: float = 0.1) -> float:
        ts = self.get_time_series(metric_name, 60.0)
        if not ts:
            return 0.0
        ema = ts[0][1]
        for _, value in ts[1:]:
            ema = alpha * value + (1 - alpha) * ema
        return ema

    @property
    def source_health(self) -> dict:
        health = {}
        for source_name in self._sources:
            points = [p for p in self._buffer[-100:] if p.source == source_name]
            if points:
                avg_quality = sum(p.quality for p in points) / len(points)
                age = time.time() - points[-1].timestamp
                health[source_name] = {
                    "points": len(points),
                    "avg_quality": round(avg_quality, 1),
                    "age_s": round(age, 2),
                    "status": "HEALTHY" if age < 5 and avg_quality > 80 else "DEGRADED",
                }
            else:
                health[source_name] = {"status": "NO_DATA"}
        return health

    @property
    def dashboard_summary(self) -> dict:
        return {
            "total_metrics": len(self._metrics),
            "total_points": len(self._buffer),
            "sources": len(self._sources),
            "stale_metrics": sum(1 for m in self._metrics.values() if m.is_stale),
        }
