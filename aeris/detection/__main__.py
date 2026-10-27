"""Train/evaluate a feature baseline, or replay test observations into a mission."""
import argparse
import json
from pathlib import Path
from .offline import read_records, train, evaluate, NormalityModel, FeatureReplayDetector


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['train', 'evaluate', 'replay'])
    p.add_argument('--data', type=Path, required=True)
    p.add_argument('--model', type=Path, required=True)
    p.add_argument('--false-alarm-rate', type=float, default=0.05)
    p.add_argument('--output', type=Path, default=Path('outputs/offline'))
    a = p.parse_args()
    rows = read_records(a.data)
    if a.action == 'train':
        model = train(rows, a.false_alarm_rate)
        model.save(a.model)
        print(json.dumps(dict(status='trained', threshold=model.threshold, dimensions=len(model.center))))
        return 0
    model = NormalityModel.load(a.model)
    if a.action == 'evaluate':
        print(json.dumps(evaluate(model, rows), indent=2))
        return 0
    from ..simulation import Simulator, Config
    detector = FeatureReplayDetector(model, rows)
    if not detector.rows or set(detector.rows) != set(range(max(detector.rows) + 1)):
        p.error('Replay needs contiguous test segments starting at zero')
    a.output.mkdir(parents=True, exist_ok=True)
    result = Simulator(Config(segments=len(detector.rows)), detector=detector).run(a.output / 'checkpoint.json')
    (a.output / 'mission.json').write_text(json.dumps(result, indent=2))
    print(json.dumps({k:v for k,v in result.items() if k not in ('events', 'observations')}))
    return 0 if result['status'] == 'completed' else 2


if __name__ == '__main__':
    raise SystemExit(main())
