"""Local image pipeline: configure, validate, train, evaluate, predict, replay."""
import argparse
import json
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    configure = sub.add_parser('configure')
    configure.add_argument('--root', type=Path, required=True)
    configure.add_argument('--names', nargs='+', required=True)
    configure.add_argument('--output', type=Path, required=True)
    for action in ('validate','train','evaluate'):
        command = sub.add_parser(action)
        command.add_argument('--data', type=Path, required=True)
        command.add_argument('--manifest', type=Path, required=True)
        if action != 'validate':
            command.add_argument('--output', type=Path, required=True)
            command.add_argument('--imgsz', type=int, default=1024)
            command.add_argument('--device', default='cpu')
        if action == 'train':
            command.add_argument('--model', default='yolov8n.pt')
            command.add_argument('--epochs', type=int, default=100)
            command.add_argument('--batch', type=int, default=4)
            command.add_argument('--seed', type=int, default=27)
            command.add_argument('--workers', type=int, default=0)
        elif action == 'evaluate':
            command.add_argument('--weights', type=Path, required=True)
            command.add_argument('--split', choices=['val','test'], default='val')
    predict = sub.add_parser('predict')
    predict.add_argument('--weights', type=Path, required=True)
    predict.add_argument('--source', type=Path, required=True)
    predict.add_argument('--output', type=Path, required=True)
    predict.add_argument('--conf', type=float, default=0.25)
    predict.add_argument('--imgsz', type=int, default=1024)
    predict.add_argument('--device', default='cpu')
    replay = sub.add_parser('replay')
    replay.add_argument('--predictions', type=Path, required=True)
    replay.add_argument('--manifest', type=Path, required=True)
    replay.add_argument('--alert-classes', nargs='+', required=True)
    replay.add_argument('--output', type=Path, required=True)
    replay.add_argument('--resume', type=Path)
    replay.add_argument('--max-sorties', type=int, default=100)
    features = sub.add_parser('features')
    features.add_argument('--weights', type=Path, required=True)
    features.add_argument('--manifest', type=Path, required=True)
    features.add_argument('--output', type=Path, required=True)
    features.add_argument('--layer', type=int, default=9)
    features.add_argument('--imgsz', type=int, default=224)
    features.add_argument('--device', default='cpu')
    a = p.parse_args()
    args = vars(a).copy()
    action = args.pop('command')
    try:
        for name in ('epochs','imgsz','batch','max_sorties'):
            if name in args and args[name] < 1:
                raise ValueError(f'{name} must be positive')
        if action == 'configure':
            import yaml
            if a.output.exists():
                raise ValueError('Configuration already exists; use a new output file')
            if len(set(a.names)) != len(a.names):
                raise ValueError('Class names must be unique')
            a.output.parent.mkdir(parents=True, exist_ok=True)
            a.output.write_text(yaml.safe_dump(dict(path=str(a.root.resolve()), train='images/train',
                val='images/val', test='images/test', names=dict(enumerate(a.names))), sort_keys=False))
            result = dict(config=str(a.output.resolve()))
        elif action == 'validate':
            from .dataset import validate
            result = validate(**args)
        else:
            from .pipeline import train_image, evaluate_image, predict_images, replay_images, extract_features
            result = {'train':train_image,'evaluate':evaluate_image,'predict':predict_images,'replay':replay_images,'features':extract_features}[action](**args)
        print(json.dumps(result, indent=2))
        return 2 if result.get('status') not in (None,'completed') else 0
    except (ValueError, FileNotFoundError, ImportError) as exc:
        p.exit(2, f'error: {exc}\n')


if __name__ == '__main__':
    raise SystemExit(main())
