import json
from pathlib import Path
import tempfile
import unittest
from aeris.config import Config
from aeris.control import SimulatedUAV
from aeris.detection.offline import read_records, train, evaluate, NormalityModel, FeatureReplayDetector
from aeris.mission import CoverageLedger
from aeris.simulation import Simulator

DATA = Path(__file__).resolve().parents[1] / 'examples/features.jsonl'


class ModuleTests(unittest.TestCase):
    def test_control_requires_launch(self):
        uav = SimulatedUAV(Config())
        with self.assertRaises(RuntimeError):
            uav.inspect_next()
        uav.launch()
        uav.inspect_next()
        self.assertEqual(uav.position, 1)
        uav.dock()
        self.assertEqual(uav.position, 0)
        self.assertFalse(uav.airborne)

    def test_coverage_cannot_skip_missing_evidence(self):
        ledger = CoverageLedger(5)
        with self.assertRaises(ValueError):
            ledger.verify(2)
        ledger.verify(0)
        ledger.verify(0)
        self.assertEqual(ledger.covered, 1)

    def test_unreachable_resume_boundary_does_not_spend_energy(self):
        s = Simulator(Config(capacity=21, seed=27), covered=39)
        self.assertEqual(s.run()['status'], 'energy_infeasible')
        self.assertEqual(s.position, 0)
        self.assertEqual(s.battery, 21)

    def test_training_serialization_and_evaluation(self):
        rows = read_records(DATA)
        model = train(rows)
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'model.json'
            model.save(path)
            restored = NormalityModel.load(path)
            self.assertEqual(model.score([1, 2]), restored.score([1, 2]))
        metrics = evaluate(model, rows)
        self.assertEqual(metrics['true_positive'], 2)
        self.assertEqual(metrics['true_negative'], 2)
        self.assertEqual(metrics['accepted'], 4)

    def test_test_labels_and_features_do_not_change_training(self):
        rows = read_records(DATA)
        before = train(rows)
        for row in rows:
            if row['split'] == 'test':
                row['features'] = [100000, -100000]
                row['label'] = 'normal'
        after = train(rows)
        self.assertEqual(before.center, after.center)
        self.assertEqual(before.threshold, after.threshold)

    def test_replay_drives_mission_and_missing_evidence_blocks(self):
        rows = read_records(DATA)
        detector = FeatureReplayDetector(train(rows), rows)
        sim = Simulator(Config(segments=4), detector=detector)
        self.assertEqual(sim.run()['status'], 'completed')
        self.assertEqual(sum(r['review_required'] for r in sim.observations), 2)
        self.assertFalse(detector.observe(100)['quality_ok'])
        missing = Simulator(Config(segments=5), detector=detector)
        self.assertEqual(missing.run()['status'], 'image_quality_blocked')
        self.assertEqual(missing.covered, 4)

    def test_split_leakage_rejected(self):
        rows = read_records(DATA)
        rows[-1]['site'] = rows[0]['site']
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'bad.jsonl'
            path.write_text('\n'.join(json.dumps(r) for r in rows))
            with self.assertRaisesRegex(ValueError, 'leakage'):
                read_records(path)

    def test_invalid_training_and_evaluation_fail(self):
        rows = read_records(DATA)
        with self.assertRaises(ValueError):
            train([r for r in rows if r['split'] != 'validation'])
        with self.assertRaises(ValueError):
            evaluate(train(rows), [r for r in rows if r['label'] == 'normal'])
        with self.assertRaises(ValueError):
            train(rows, false_alarm_rate=0)


if __name__ == '__main__':
    unittest.main()
