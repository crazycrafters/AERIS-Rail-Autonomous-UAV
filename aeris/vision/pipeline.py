"""Optional Ultralytics wrappers; local inference only, no aircraft control."""
import json
from pathlib import Path
import platform
from .dataset import sha256, validate


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, allow_nan=False))


def new_directory(path):
    path = Path(path).resolve()
    if path.exists():
        raise ValueError(f'Refusing to overwrite run: {path}; choose a new output path')
    path.mkdir(parents=True)
    return path


def train_image(data, manifest, output, model='yolov8n.pt', epochs=100,
                imgsz=1024, batch=4, device='cpu', seed=27, workers=0):
    audit = validate(data, manifest)
    from ultralytics import YOLO
    import ultralytics
    import torch
    run = new_directory(output)
    write_json(run / 'dataset-audit.json', audit)
    settings = dict(data=str(Path(data).resolve()), epochs=epochs, imgsz=imgsz,
                    batch=batch, device=device, seed=seed, workers=workers,
                    project=str(run), name='fit', exist_ok=False, plots=True,
                    # Avoid automatic AMP weight downloads; keep first run simple.
                    amp=False)
    write_json(run / 'provenance.json', dict(initial_model=str(model), settings=settings,
                python=platform.python_version(), ultralytics=ultralytics.__version__,
                torch=torch.__version__, dataset=audit))
    detector = YOLO(str(model))
    detector.train(**settings)
    # Use actual framework output, never assume a stale run path is current.
    actual = Path(detector.trainer.save_dir)
    best = actual / 'weights' / 'best.pt'
    if not best.is_file():
        raise RuntimeError('Training returned without best.pt; inspect the current run logs')
    report = dict(best_pt=str(best.resolve()), sha256=sha256(best), run=str(actual.resolve()))
    write_json(run / 'training-result.json', report)
    return report


def evaluate_image(data, manifest, weights, output, split='val', imgsz=1024, device='cpu'):
    if split not in ('val', 'test'):
        raise ValueError('Evaluate only val or test')
    audit = validate(data, manifest)
    weights = Path(weights).resolve(strict=True)
    from ultralytics import YOLO
    run = new_directory(output)
    metrics = YOLO(str(weights)).val(data=str(Path(data).resolve()), split=split,
                 imgsz=imgsz, device=device, workers=0, project=str(run), name='metrics', plots=True)
    report = dict(split=split, weights_sha256=sha256(weights), dataset=audit,
                  metrics={str(k): float(v) for k,v in metrics.results_dict.items()})
    write_json(run / 'evaluation.json', report)
    return report


def predict_images(weights, source, output, conf=0.25, imgsz=1024, device='cpu'):
    if not 0 <= conf <= 1:
        raise ValueError('Confidence must be in [0,1]')
    weights = Path(weights).resolve(strict=True)
    source = Path(source).resolve(strict=True)
    images = sorted(p for p in source.rglob('*') if p.is_file() and p.suffix.lower() in ('.jpg','.jpeg','.png','.bmp')) if source.is_dir() else [source]
    if not images:
        raise ValueError('No images to predict')
    from ultralytics import YOLO
    model = YOLO(str(weights))
    run = new_directory(output)
    model_hash = sha256(weights)
    predictions = []
    for index, image in enumerate(images):
        results = model.predict(source=str(image), conf=conf, imgsz=imgsz, device=device, verbose=False)
        result = results[0]
        detections = [dict(class_id=int(b.cls.item()), class_name=result.names[int(b.cls.item())],
                           confidence=float(b.conf.item()), xyxy=b.xyxy[0].tolist()) for b in result.boxes]
        record = dict(image=str(image), image_sha256=sha256(image), weights_sha256=model_hash,
                      width=int(result.orig_shape[1]), height=int(result.orig_shape[0]),
                      detections=detections, class_names=list(result.names.values()),
                      quality_ok=None, anomaly_score=None)
        predictions.append(record)
        result.save(filename=str(run / f'{index:06d}-{image.stem}.jpg'))
    write_json(run / 'predictions.json', predictions)
    return dict(images=len(predictions), predictions=str(run / 'predictions.json'))


class ImageReplayDetector:
    """Replay reviewed image results; predictions alone never certify coverage."""
    def __init__(self, predictions, manifest, alert_classes):
        records = json.loads(Path(predictions).read_text())
        by_hash = {}
        for record in records:
            key = record['image_sha256']
            if key in by_hash:
                raise ValueError('Duplicate image content in predictions')
            by_hash[key] = record
        model_hashes = {r.get('weights_sha256') for r in records}
        if len(model_hashes) != 1 or None in model_hashes:
            raise ValueError('Replay needs predictions from exactly one identified model')
        declared = {name for r in records for name in r.get('class_names', [])}
        if declared and not set(alert_classes) <= declared:
            raise ValueError('Alert classes must match model class names')
        self.rows = {}
        rows = json.loads(Path(manifest).read_text())
        for row in rows:
            segment = row.get('segment')
            if type(segment) is not int or segment < 0 or segment in self.rows:
                raise ValueError('Unique nonnegative segment required')
            if type(row.get('quality_ok')) is not bool or type(row.get('asset_observed')) is not bool:
                raise ValueError('Explicit quality_ok and asset_observed booleans required')
            image = Path(row['image'])
            if not image.is_absolute():
                image = Path(manifest).resolve().parent / image
            digest = sha256(image)
            if digest not in by_hash:
                raise ValueError(f'Missing predictions for {image}')
            predicted = by_hash[digest]
            if predicted.get('weights_sha256') is None:
                raise ValueError('Missing model provenance')
            boxes = predicted['detections']
            flagged = [b for b in boxes if b['class_name'] in alert_classes]
            self.rows[segment] = dict(segment=segment,
                quality_ok=row['quality_ok'] and row['asset_observed'],
                known_score=max((b['confidence'] for b in flagged),default=0.0),
                anomaly_score=None, review_required=bool(flagged) and row['quality_ok'] and row['asset_observed'],
                evidence_id=digest, weights_sha256=predicted['weights_sha256'], detections=boxes)
        if not self.rows or set(self.rows) != set(range(len(self.rows))):
            raise ValueError('Replay needs contiguous segments from zero')
        self.alert_classes = list(alert_classes)

    def observe(self, segment):
        return self.rows[segment]


def replay_images(predictions, manifest, alert_classes, output, resume=None, max_sorties=100):
    from ..simulation import Config, Simulator
    detector = ImageReplayDetector(predictions, manifest, alert_classes)
    if resume:
        previous = json.loads((Path(resume).parent / 'mission.json').read_text())
        if (previous.get('predictions_sha256') != sha256(predictions)
                or previous.get('manifest_sha256') != sha256(manifest)
                or previous.get('alert_classes') != list(alert_classes)):
            raise ValueError('Replay inputs differ from checkpoint run')
        sim = Simulator.load(resume, detector=detector)
        if sim.config.segments != len(detector.rows):
            raise ValueError('Checkpoint route length does not match image manifest')
    else:
        sim = Simulator(Config(segments=len(detector.rows)), detector=detector)
    run = new_directory(output)
    result = sim.run(run / 'checkpoint.json', max_sorties=max_sorties)
    result['predictions_sha256'] = sha256(predictions)
    result['manifest_sha256'] = sha256(manifest)
    result['alert_classes'] = list(alert_classes)
    write_json(run / 'mission.json', result)
    return {k:v for k,v in result.items() if k not in ('events','observations')}


def extract_features(weights, manifest, output, layer=9, imgsz=224, device='cpu'):
    """Frozen YOLOv8 layer embeddings for pre-cropped assets; no fitting here."""
    from ultralytics import YOLO
    from .dataset import sha256
    from ..detection.offline import read_records
    weights = Path(weights).resolve(strict=True)
    manifest = Path(manifest).resolve(strict=True)
    output = Path(output)
    if output.exists():
        raise ValueError('Feature output exists; choose a new file')
    if layer < 0:
        raise ValueError('Use a nonnegative embedding layer index')
    rows = [json.loads(line) for line in manifest.read_text().splitlines() if line.strip()]
    if not rows:
        raise ValueError('Empty image-feature manifest')
    model = YOLO(str(weights))
    if layer >= len(model.model.model):
        raise ValueError('Embedding layer out of model bounds')
    features = []
    model_hash = sha256(weights)
    for row in rows:
        image = Path(row['image'])
        if not image.is_absolute():
            image = manifest.parent / image
        image = image.resolve(strict=True)
        embedded = model.predict(source=str(image), embed=[layer], imgsz=imgsz, device=device, verbose=False)
        vector = embedded[0].detach().cpu().flatten().tolist()
        result = dict(row, image=str(image), features=vector, image_sha256=sha256(image),
                      encoder_sha256=model_hash, embedding_layer=layer, embedding_imgsz=imgsz)
        features.append(result)
    # Validate generated schema and split isolation before making the output visible.
    output.parent.mkdir(parents=True, exist_ok=True)
    temp = output.with_suffix(output.suffix + '.tmp')
    try:
        temp.write_text(''.join(json.dumps(r, allow_nan=False)+'\n' for r in features))
        read_records(temp)
        temp.replace(output)
    finally:
        temp.unlink(missing_ok=True)
    return dict(records=len(features), dimensions=len(features[0]['features']), output=str(output.resolve()),
                encoder_sha256=model_hash, layer=layer)
