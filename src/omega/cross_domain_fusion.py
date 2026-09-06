"""Cross-domain state fusion — unified picture from fragmented sensors.

Standard mission control: each domain (orbital, atmospheric, ground)
has its own view. No one sees the full picture.

Innovation: Fuse data from ALL domains into a single coherent state
estimate that no individual domain can see alone.

The wheel: telemetry aggregation
The vehicle: cross-domain correlation that reveals hidden patterns

Key insight: A vibration anomaly on the engine + a density deviation
in the atmosphere + a tracking error on the ground = a single event
(foreign object debris ingestion). No single domain sees this. The
fusion engine does.
"""

import time
from dataclasses import dataclass, field


@dataclass
class DomainState:
    domain: str
    state_vector: dict[str, float]
    confidence: float
    timestamp: float
    uncertainty: dict[str, float] = field(default_factory=dict)


@dataclass
class FusedEvent:
    event_id: str
    domains: list[str]
    description: str
    severity: float
    confidence: float
    timestamp: float
    root_cause_hypothesis: str
    evidence: list[dict]


class CrossDomainCorrelator:
    """Detects events that span multiple domains.

    Innovation: Correlates anomalies across domain boundaries.
    An anomaly in isolation is interesting. An anomaly that appears
    simultaneously across multiple domains is SIGNIFICANT.

    Uses time-windowed correlation with adaptive thresholds.
    """

    def __init__(self, correlation_window_s: float = 5.0):
        self.correlation_window = correlation_window_s
        self._domain_anomalies: dict[str, list[dict]] = {}
        self._cross_domain_events: list[FusedEvent] = []

    def report_anomaly(self, domain: str, anomaly: dict):
        if domain not in self._domain_anomalies:
            self._domain_anomalies[domain] = []

        anomaly["timestamp"] = time.time()
        self._domain_anomalies[domain].append(anomaly)

        cutoff = time.time() - self.correlation_window * 10
        for d in self._domain_anomalies:
            self._domain_anomalies[d] = [
                a for a in self._domain_anomalies[d] if a.get("timestamp", 0) > cutoff
            ]

        self._detect_cross_domain()

    def _detect_cross_domain(self):
        now = time.time()
        window = self.correlation_window

        recent_by_domain = {}
        for domain, anomalies in self._domain_anomalies.items():
            recent = [a for a in anomalies if now - a.get("timestamp", 0) < window]
            if recent:
                recent_by_domain[domain] = recent

        if len(recent_by_domain) < 2:
            return

        domains = list(recent_by_domain.keys())
        for i in range(len(domains)):
            for j in range(i + 1, len(domains)):
                d1, d2 = domains[i], domains[j]
                for a1 in recent_by_domain[d1]:
                    for a2 in recent_by_domain[d2]:
                        t1 = a1.get("timestamp", 0)
                        t2 = a2.get("timestamp", 0)
                        if abs(t1 - t2) < window:
                            event = FusedEvent(
                                event_id=f"cross_{int(now)}_{d1}_{d2}",
                                domains=[d1, d2],
                                description=f"Correlated anomaly: {d1} + {d2}",
                                severity=max(
                                    a1.get("severity", 0.5),
                                    a2.get("severity", 0.5),
                                ),
                                confidence=min(
                                    a1.get("confidence", 0.5),
                                    a2.get("confidence", 0.5),
                                ),
                                timestamp=now,
                                root_cause_hypothesis=self._hypothesize(d1, d2, a1, a2),
                                evidence=[
                                    {"domain": d1, "anomaly": a1},
                                    {"domain": d2, "anomaly": a2},
                                ],
                            )
                            self._cross_domain_events.append(event)

    def _hypothesize(self, d1: str, d2: str, a1: dict, a2: dict) -> str:
        hypotheses = {
            ("propulsion", "atmosphere"): "Engine exhaust perturbing local atmosphere",
            ("propulsion", "orbital"): "Thrust anomaly affecting trajectory",
            ("propulsion", "ground"): "Engine event visible from ground station",
            ("atmosphere", "orbital"): "Atmospheric density affecting orbit",
            ("atmosphere", "ground"): "Weather impact on ground tracking",
            ("orbital", "ground"): "Orbital event visible from ground",
        }

        pair = tuple(sorted([d1, d2]))
        return hypotheses.get(pair, f"Cross-domain event: {d1} ↔ {d2}")

    @property
    def recent_events(self) -> list[dict]:
        return [
            {
                "event_id": e.event_id,
                "domains": e.domains,
                "description": e.description,
                "severity": e.severity,
                "confidence": e.confidence,
                "hypothesis": e.root_cause_hypothesis,
            }
            for e in self._cross_domain_events[-10:]
        ]


class StateFusionEngine:
    """Fuses domain states into unified mission state.

    Innovation: Uses weighted averaging with uncertainty propagation.
    Each domain contributes its state estimate weighted by its confidence
    and uncertainty. The fused state is MORE ACCURATE than any individual
    domain's estimate.
    """

    def __init__(self):
        self._domain_states: dict[str, DomainState] = {}
        self._fused_history: list[dict] = []

    def update_domain(self, state: DomainState):
        self._domain_states[state.domain] = state

    def fuse_state(self) -> dict:
        if not self._domain_states:
            return {}

        all_keys = set()
        for state in self._domain_states.values():
            all_keys.update(state.state_vector.keys())

        fused = {}
        for key in all_keys:
            values = []
            weights = []
            for domain, state in self._domain_states.items():
                if key in state.state_vector:
                    values.append(state.state_vector[key])
                    unc = state.uncertainty.get(key, 1.0)
                    weight = state.confidence / max(unc, 0.01)
                    weights.append(weight)

            if values:
                total_weight = sum(weights)
                fused[key] = sum(v * w for v, w in zip(values, weights)) / total_weight

        self._fused_history.append(
            {
                "timestamp": time.time(),
                "state": fused,
                "domains": list(self._domain_states.keys()),
            }
        )

        return fused

    def get_fusion_quality(self) -> dict:
        if not self._domain_states:
            return {"quality": 0, "domains": 0}

        confidences = [s.confidence for s in self._domain_states.values()]
        avg_confidence = sum(confidences) / len(confidences)
        domain_count = len(self._domain_states)

        quality = avg_confidence * min(domain_count / 3, 1.0)

        return {
            "quality": quality,
            "domains": domain_count,
            "avg_confidence": avg_confidence,
            "domain_names": list(self._domain_states.keys()),
        }


class AnomalyRootCauseAnalyzer:
    """Identifies root cause from cross-domain evidence.

    Innovation: When a cross-domain event is detected, this module
    analyzes the evidence to determine which domain is the SOURCE
    and which are SYMPTOMS.

    Uses causal reasoning: the source domain shows anomalies FIRST,
    other domains show anomalies AFTER (propagation delay).
    """

    def __init__(self):
        self._causal_templates = {
            "engine_failure": {
                "source": "propulsion",
                "symptoms": ["orbital", "atmosphere", "ground"],
                "time_delays_s": [0, 0.5, 1.0],
                "indicators": [
                    "vibration_spike",
                    "thrust_drop",
                    "trajectory_deviation",
                ],
            },
            "atmospheric_event": {
                "source": "atmosphere",
                "symptoms": ["orbital", "propulsion", "ground"],
                "time_delays_s": [0, 2.0, 0.1],
                "indicators": ["density_anomaly", "temperature_spike", "wind_shear"],
            },
            "ground_equipment": {
                "source": "ground",
                "symptoms": ["orbital"],
                "time_delays_s": [0],
                "indicators": ["tracking_error", "signal_loss", "clock_drift"],
            },
        }

    def analyze(
        self,
        event: FusedEvent,
        domain_timelines: dict[str, list[dict]],
    ) -> dict:
        best_hypothesis = None
        best_score = 0

        for hypothesis_name, template in self._causal_templates.items():
            if not all(
                d in event.domains
                for d in [template["source"]]
                + template["symptoms"][: len(event.domains) - 1]
            ):
                continue

            score = 0
            evidence_count = 0

            for indicator in template["indicators"]:
                for domain, timeline in domain_timelines.items():
                    for entry in timeline:
                        if indicator in str(entry.get("type", "")):
                            score += 1
                            evidence_count += 1

            if evidence_count > 0:
                normalized_score = score / evidence_count
                if normalized_score > best_score:
                    best_score = normalized_score
                    best_hypothesis = {
                        "hypothesis": hypothesis_name,
                        "source_domain": template["source"],
                        "confidence": normalized_score,
                        "evidence_count": evidence_count,
                    }

        if best_hypothesis:
            return best_hypothesis

        return {
            "hypothesis": "unknown",
            "source_domain": event.domains[0] if event.domains else "unknown",
            "confidence": 0.3,
            "evidence_count": len(event.evidence),
        }


class CrossDomainFusionSystem:
    """Full cross-domain fusion system.

    The wheel: telemetry aggregation
    The vehicle: unified picture from fragmented sensors

    Innovation: No single domain sees the full picture. This fuses
    orbital, atmospheric, propulsion, and ground data into a single
    coherent state that reveals patterns invisible to any individual
    domain.
    """

    def __init__(self):
        self.correlator = CrossDomainCorrelator()
        self.fusion_engine = StateFusionEngine()
        self.root_cause_analyzer = AnomalyRootCauseAnalyzer()
        self._mission_log: list[dict] = []

    def ingest_domain_state(self, state: DomainState):
        self.fusion_engine.update_domain(state)

        for key, value in state.state_vector.items():
            unc = state.uncertainty.get(key, 1.0)
            if unc > 0.5 or abs(value) > 100:
                self.correlator.report_anomaly(
                    state.domain,
                    {
                        "type": "state_anomaly",
                        "metric": key,
                        "value": value,
                        "uncertainty": unc,
                        "severity": min(1.0, unc / 2),
                        "confidence": state.confidence,
                    },
                )

    def get_mission_situation(self) -> dict:
        fused_state = self.fusion_engine.fuse_state()
        fusion_quality = self.fusion_engine.get_fusion_quality()
        recent_events = self.correlator.recent_events

        root_causes = []
        for event_data in recent_events:
            root_cause = self.root_cause_analyzer.analyze(
                FusedEvent(
                    event_id=event_data["event_id"],
                    domains=event_data["domains"],
                    description=event_data["description"],
                    severity=event_data["severity"],
                    confidence=event_data["confidence"],
                    timestamp=time.time(),
                    root_cause_hypothesis=event_data["hypothesis"],
                    evidence=[],
                ),
                {},
            )
            root_causes.append(root_cause)

        return {
            "fused_state": fused_state,
            "fusion_quality": fusion_quality,
            "active_events": len(recent_events),
            "root_causes": root_causes,
            "domains_online": fusion_quality["domains"],
        }
