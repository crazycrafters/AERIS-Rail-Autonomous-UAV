"""Deterministic one-dimensional corridor simulator with durable checkpoints.

Energy units are abstract; the return model is an oracle for this simplified
world. This is software validation, not an aircraft performance model.
"""
from dataclasses import dataclass, asdict
import json
from pathlib import Path
import random


@dataclass(frozen=True)
class Config:
    segments: int = 40
    segment_km: float = 0.1
    capacity: float = 100.0
    reserve: float = 15.0
    uncertainty: float = 5.0
    travel_per_km: float = 4.0
    inspect_energy: float = 2.0
    wind_multiplier: float = 1.2
    threshold: float = 0.65
    seed: int = 7

    def __post_init__(self):
        import math
        numeric = (self.segment_km, self.capacity, self.reserve, self.uncertainty,
                   self.travel_per_km, self.inspect_energy, self.wind_multiplier,
                   self.threshold)
        if not all(math.isfinite(x) for x in numeric):
            raise ValueError("Configuration must be finite")
        if isinstance(self.segments, bool) or not isinstance(self.segments, int) or self.segments < 1:
            raise ValueError("segments must be a positive integer")
        if min(self.segment_km, self.capacity, self.travel_per_km, self.inspect_energy, self.wind_multiplier) <= 0:
            raise ValueError("Physical parameters must be positive")
        if min(self.reserve, self.uncertainty) < 0 or self.reserve + self.uncertainty >= self.capacity:
            raise ValueError("Invalid reserve or uncertainty")
        if not 0 <= self.threshold <= 1:
            raise ValueError("threshold must be in [0, 1]")


class Simulator:
    def __init__(self, config=Config(), covered=0):
        if isinstance(covered, bool) or not isinstance(covered, int) or not 0 <= covered <= config.segments:
            raise ValueError("Invalid coverage checkpoint")
        self.config = config
        self.covered = covered
        self.events = []
        self.observations = []
        self.sortie = 0
        self.battery = config.capacity
        self.position = 0

    def travel(self, segments):
        c = self.config
        return abs(segments) * c.segment_km * c.travel_per_km * c.wind_multiplier

    def emit(self, kind, **details):
        self.events.append(dict(event=kind, sortie=self.sortie, position=self.position,
                                battery=round(self.battery, 6), **details))

    def observe(self, segment):
        # Seed per asset makes replay independent of interruptions and sortie count.
        rng = random.Random(self.config.seed + segment * 1009)
        truth = segment % 11 == 5
        quality = rng.random() > 0.08
        known = min(1.0, rng.random() * 0.35 + (0.6 if truth and segment % 2 else 0))
        unknown = min(1.0, rng.random() * 0.45 + (0.5 if truth else 0))
        alert = quality and max(known, unknown) >= self.config.threshold
        return dict(segment=segment, quality_ok=quality, known_score=known,
                    anomaly_score=unknown, review_required=alert, synthetic_truth=truth)

    def run(self, checkpoint=None, max_sorties=100):
        c = self.config
        for _ in range(max_sorties):
            if self.covered == c.segments:
                return self.result("completed")
            self.sortie += 1
            self.battery = c.capacity
            self.position = 0
            before = self.covered
            self.emit("launch")
            # Reinspect one segment of overlap on subsequent sorties.
            start = max(0, self.covered - 1)
            self.battery -= self.travel(start)
            self.position = start
            while self.position < c.segments:
                target = self.position + 1
                inspection_cost = self.travel(1) + c.inspect_energy
                required = inspection_cost + self.travel(target) + c.reserve + c.uncertainty
                if self.battery + 1e-9 < required:
                    self.emit("return_required", required_energy=required)
                    break
                self.battery -= inspection_cost
                self.position = target
                observation = self.observe(target - 1)
                self.observations.append(observation)
                # Low quality never counts as verified coverage. Retry is deferred.
                if not observation["quality_ok"]:
                    self.emit("quality_rejected", segment=target - 1)
                    break
                self.covered = max(self.covered, target)
                self.emit("inspection_verified", segment=target - 1,
                          review_required=observation["review_required"])
            self.battery -= self.travel(self.position)
            self.position = 0
            if self.battery < c.reserve - 1e-9:
                raise RuntimeError("Reserve invariant violated")
            self.emit("docked", covered=self.covered)
            if checkpoint:
                self.save(checkpoint)
            if self.covered == c.segments:
                return self.result("completed")
            if self.covered == before:
                # Distinguish persistent image rejection from energy infeasibility.
                reason = "image_quality_blocked" if self.events[-2]["event"] == "quality_rejected" else "energy_infeasible"
                return self.result(reason)
            self.emit("charging_complete")
        return self.result("sortie_limit")

    def result(self, status):
        return dict(status=status, covered_segments=self.covered,
                    total_segments=self.config.segments, sorties=self.sortie,
                    events=self.events, observations=self.observations)

    def save(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(path.suffix + ".tmp")
        temp.write_text(json.dumps(dict(version=1, config=asdict(self.config), covered=self.covered), indent=2))
        temp.replace(path)

    @classmethod
    def load(cls, path):
        data = json.loads(Path(path).read_text())
        if data["version"] != 1:
            raise ValueError("Unsupported checkpoint version")
        return cls(Config(**data["config"]), data["covered"])
