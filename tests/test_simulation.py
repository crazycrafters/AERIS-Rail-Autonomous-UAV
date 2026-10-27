import json
from pathlib import Path
import tempfile
import unittest
from aeris.simulation import Config, Simulator


class MissionTests(unittest.TestCase):
    def test_complete_multiple_sorties_and_reserve(self):
        s = Simulator(Config(seed=27))
        r = s.run()
        self.assertEqual(r['status'], 'completed')
        self.assertGreater(r['sorties'], 1)
        self.assertEqual(s.covered, 40)
        self.assertTrue(all(e['battery'] >= 15 for e in s.events if e['event'] == 'docked'))
        verified = {e['segment'] for e in s.events if e['event'] == 'inspection_verified'}
        self.assertEqual(verified, set(range(40)))

    def test_resume_matches_uninterrupted_coverage(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'checkpoint.json'
            s = Simulator(Config(seed=27))
            self.assertEqual(s.run(p, max_sorties=1)['status'], 'sortie_limit')
            covered = s.covered
            restored = Simulator.load(p)
            self.assertEqual(restored.covered, covered)
            self.assertEqual(restored.run(p)['status'], 'completed')
            self.assertEqual(restored.observations[0]['segment'], covered - 1)
            self.assertEqual(json.loads(p.read_text())['covered'], 40)

    def test_insufficient_capacity_returns_without_false_coverage(self):
        s = Simulator(Config(capacity=21, seed=27))
        r = s.run()
        self.assertEqual(r['status'], 'energy_infeasible')
        self.assertEqual(s.covered, 0)
        self.assertEqual(s.battery, 21)

    def test_bad_image_blocks_coverage(self):
        s = Simulator(Config(seed=0))
        self.assertEqual(s.run()['status'], 'image_quality_blocked')
        self.assertEqual(s.covered, 4)
        self.assertFalse(s.observe(4)['quality_ok'])

    def test_invalid_config(self):
        for args in ({'capacity': float('nan')}, {'reserve': 100}, {'segments': 0}, {'threshold': 2}):
            with self.assertRaises(ValueError):
                Config(**args)

    def test_completed_checkpoint_does_not_relaunch(self):
        s = Simulator(Config(seed=27), covered=40)
        self.assertEqual(s.run()['sorties'], 0)


if __name__ == '__main__':
    unittest.main()
