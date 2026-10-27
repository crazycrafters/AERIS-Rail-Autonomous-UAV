"""Deterministic one-dimensional corridor simulator with durable checkpoints.

Energy units are abstract; the return model is an oracle for this simplified
world. This is software validation, not an aircraft performance model.
"""
from .config import Config
from .detection import SyntheticDetector
from .control import SimulatedUAV
from .mission import EnergySupervisor, CoverageLedger
from .persistence import save_checkpoint, load_checkpoint


class Simulator:
    def __init__(self, config=Config(), covered=0, detector=None):
        if isinstance(covered, bool) or not isinstance(covered, int) or not 0 <= covered <= config.segments:
            raise ValueError("Invalid coverage checkpoint")
        self.config = config
        self.ledger = CoverageLedger(config.segments, covered)
        self.detector = detector if detector is not None else SyntheticDetector(config.seed, config.threshold)
        self.uav = SimulatedUAV(config)
        self.supervisor = EnergySupervisor(config)
        self.events = []
        self.observations = []
        self.sortie = 0

    @property
    def covered(self):
        return self.ledger.covered

    @property
    def battery(self):
        return self.uav.battery

    @property
    def position(self):
        return self.uav.position

    def travel(self, segments):
        return self.uav.travel_energy(segments)

    def emit(self, kind, **details):
        self.events.append(dict(event=kind, sortie=self.sortie, position=self.position,
                                battery=round(self.battery, 6), **details))

    def observe(self, segment):
        return self.detector.observe(segment)

    def run(self, checkpoint=None, max_sorties=100):
        c = self.config
        if isinstance(max_sorties, bool) or not isinstance(max_sorties, int) or max_sorties < 1:
            raise ValueError("max_sorties must be a positive integer")
        for _ in range(max_sorties):
            if self.covered == c.segments:
                return self.result("completed")
            self.sortie += 1
            self.uav.launch()
            before = self.covered
            self.emit("launch")
            # Reinspect one segment of overlap on subsequent sorties.
            start = self.ledger.resume_start
            if not self.supervisor.can_reposition(self.battery, start):
                self.emit("return_required", reason="checkpoint_unreachable")
                self.uav.dock()
                self.emit("docked", covered=self.covered)
                if checkpoint:
                    self.save(checkpoint)
                return self.result("energy_infeasible")
            self.uav.move_to(start)
            while self.position < c.segments:
                target = self.position + 1
                required = self.supervisor.required_for_inspection(self.position, target)
                if self.battery + 1e-9 < required:
                    self.emit("return_required", required_energy=required)
                    break
                self.uav.inspect_next()
                observation = self.observe(target - 1)
                self.observations.append(observation)
                # Low quality never counts as verified coverage. Retry is deferred.
                if not observation["quality_ok"]:
                    self.emit("quality_rejected", segment=target - 1)
                    break
                self.ledger.verify(target - 1)
                self.emit("inspection_verified", segment=target - 1,
                          review_required=observation["review_required"])
            self.uav.dock()
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
        save_checkpoint(path, self.config, self.covered)

    @classmethod
    def load(cls, path, detector=None):
        config, covered = load_checkpoint(path)
        return cls(config, covered, detector)
