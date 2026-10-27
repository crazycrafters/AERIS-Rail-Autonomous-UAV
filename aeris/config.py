"""Validated mission configuration in abstract simulation energy units."""
from dataclasses import dataclass


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

