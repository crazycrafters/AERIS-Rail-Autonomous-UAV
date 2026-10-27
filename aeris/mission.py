"""Energy constraints and contiguous evidence coverage, independent of perception."""
from .control import SimulatedUAV


class EnergySupervisor:
    def __init__(self, config):
        self.config = config
        self.energy_model = SimulatedUAV(config)

    def required_for_inspection(self, position, target):
        c = self.config
        travel = self.energy_model.travel_energy
        return travel(target - position) + c.inspect_energy + travel(target) + c.reserve + c.uncertainty

    def can_reposition(self, battery, target):
        c = self.config
        required = 2 * self.energy_model.travel_energy(target) + c.reserve + c.uncertainty
        return battery + 1e-9 >= required


class CoverageLedger:
    def __init__(self, total, covered=0):
        if isinstance(covered, bool) or not isinstance(covered, int) or not 0 <= covered <= total:
            raise ValueError("Invalid coverage boundary")
        self.total = total
        self.covered = covered

    @property
    def resume_start(self):
        return max(0, self.covered - 1)

    def verify(self, segment):
        if not 0 <= segment < self.total or segment > self.covered:
            raise ValueError("Cannot verify out-of-order or invalid coverage")
        self.covered = max(self.covered, segment + 1)
