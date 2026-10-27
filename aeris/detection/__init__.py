"""Inspection backend contract and deterministic synthetic implementation."""
from typing import Protocol, TypedDict
import random


class Observation(TypedDict):
    segment: int
    quality_ok: bool
    known_score: float
    anomaly_score: float
    review_required: bool


class Detector(Protocol):
    def observe(self, segment: int) -> Observation: ...


class SyntheticDetector:
    """Software fixture only: no image processing or learned detection."""
    def __init__(self, seed=7, threshold=0.65):
        self.seed = seed
        self.threshold = threshold

    def observe(self, segment):
        rng = random.Random(self.seed + segment * 1009)
        truth = segment % 11 == 5
        quality = rng.random() > 0.08
        known = min(1.0, rng.random() * 0.35 + (0.6 if truth and segment % 2 else 0))
        unknown = min(1.0, rng.random() * 0.45 + (0.5 if truth else 0))
        return dict(segment=segment, quality_ok=quality, known_score=known,
                    anomaly_score=unknown,
                    review_required=quality and max(known, unknown) >= self.threshold,
                    synthetic_truth=truth)
