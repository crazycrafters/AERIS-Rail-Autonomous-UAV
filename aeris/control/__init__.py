"""Mission-level control interface; only an abstract simulator is implemented."""
from typing import Protocol


class UAV(Protocol):
    position: int
    battery: float
    def launch(self) -> None: ...
    def move_to(self, segment_boundary: int) -> None: ...
    def inspect_next(self) -> None: ...
    def dock(self) -> None: ...


class SimulatedUAV:
    """No aircraft transport, dynamics, geographical coordinates, or arming."""
    def __init__(self, config):
        self.config = config
        self.position = 0
        self.battery = config.capacity
        self.airborne = False

    def travel_energy(self, segments):
        c = self.config
        return abs(segments) * c.segment_km * c.travel_per_km * c.wind_multiplier

    def launch(self):
        if self.airborne or self.position != 0:
            raise RuntimeError("Launch requires docked state")
        self.battery = self.config.capacity
        self.airborne = True

    def _consume(self, energy):
        if not self.airborne:
            raise RuntimeError("Movement requires launch")
        if energy > self.battery + 1e-9:
            raise RuntimeError("Insufficient simulated energy")
        self.battery -= energy

    def move_to(self, segment_boundary):
        if not isinstance(segment_boundary, int) or not 0 <= segment_boundary <= self.config.segments:
            raise ValueError("Invalid corridor position")
        self._consume(self.travel_energy(segment_boundary - self.position))
        self.position = segment_boundary

    def inspect_next(self):
        if self.position >= self.config.segments:
            raise ValueError("End of corridor")
        self._consume(self.travel_energy(1) + self.config.inspect_energy)
        self.position += 1

    def dock(self):
        self.move_to(0)
        self.airborne = False
