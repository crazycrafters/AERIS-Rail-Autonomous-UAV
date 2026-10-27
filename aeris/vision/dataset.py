"""Strict YOLO box-dataset audit, including a site-separated metadata manifest."""
import csv
import hashlib
import math
from pathlib import Path


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def read_config(path):
    import yaml
    path = Path(path).resolve()
    config = yaml.safe_load(path.read_text())
    if not isinstance(config, dict):
        raise ValueError('Expected a YAML mapping')
    names = config.get('names')
    if isinstance(names, dict):
        if set(names) != set(range(len(names))):
            raise ValueError('Class IDs must be consecutive integers from zero')
        names = [names[i] for i in range(len(names))]
    if not isinstance(names, list) or not names or not all(isinstance(n, str) and n for n in names) or len(set(names)) != len(names):
        raise ValueError('Expected unique nonempty class names')
    root = Path(config.get('path', '.'))
    if not root.is_absolute():
        root = path.parent / root
    root = root.resolve()
    splits = {}
    for split in ('train', 'val', 'test'):
        value = config.get(split)
        if not isinstance(value, str):
            raise ValueError('This tool requires one image directory per train/val/test split')
        directory = (root / value).resolve()
        if directory != root / 'images' / split:
            raise ValueError(f'Expected images/{split} layout')
        splits[split] = directory
    return root, names, splits


def validate(data, manifest):
    from PIL import Image
    root, names, splits = read_config(data)
    with Path(manifest).open(newline='') as stream:
        reader = csv.DictReader(stream)
        if not {'image', 'site', 'session', 'asset_group', 'split'} <= set(reader.fieldnames or []):
            raise ValueError('Manifest needs image,site,session,asset_group,split columns')
        rows = list(reader)
    indexed = {}
    groups = {}
    for row in rows:
        key = row['image']
        if not key or key in indexed or row['split'] not in splits:
            raise ValueError('Duplicate image or invalid manifest split')
        indexed[key] = row
        for field in ('site', 'session', 'asset_group'):
            if not row[field].strip():
                raise ValueError(f'Missing {field} for {key}')
            # Session and asset IDs must be globally unique or qualified by site.
            group = (field, row[field])
            previous = groups.setdefault(group, row['split'])
            if previous != row['split']:
                raise ValueError(f'{field} leakage across splits: {row[field]}')
    seen_images = set()
    hashes = {}
    counts = {}
    content_hash = hashlib.sha256()
    for split, directory in splits.items():
        images = sorted(p for p in directory.rglob('*') if p.is_file() and p.suffix.lower() in ('.jpg', '.jpeg', '.png', '.bmp'))
        if not images:
            raise ValueError(f'No images in {directory}')
        label_root = root / 'labels' / split
        expected_labels = set()
        class_counts = [0] * len(names)
        for image in images:
            key = image.relative_to(root).as_posix()
            row = indexed.get(key)
            if row is None or row['split'] != split:
                raise ValueError(f'Missing or wrong manifest entry: {key}')
            seen_images.add(key)
            digest = sha256(image)
            if digest in hashes and hashes[digest] != split:
                raise ValueError(f'Duplicate image content across splits: {key}')
            hashes[digest] = split
            with Image.open(image) as decoded:
                if min(decoded.size) < 2:
                    raise ValueError(f'Image too small: {key}')
                decoded.verify()
            label = label_root / image.relative_to(directory).with_suffix('.txt')
            if label in expected_labels:
                raise ValueError(f'Images with same stem share label: {label}')
            expected_labels.add(label)
            if not label.is_file():
                raise ValueError(f'Missing annotation (use empty file for reviewed negative): {label}')
            content_hash.update(f'{key}:{digest}:{sha256(label)}\n'.encode())
            for line in label.read_text().splitlines():
                if not line.strip():
                    continue
                values = line.split()
                if len(values) != 5:
                    raise ValueError(f'Expected YOLO detection box, not segmentation: {label}')
                cls, x, y, w, h = map(float, values)
                if not all(math.isfinite(v) for v in (cls, x, y, w, h)):
                    raise ValueError(f'Nonfinite label: {label}')
                if not cls.is_integer() or not 0 <= cls < len(names):
                    raise ValueError(f'Invalid class: {label}')
                if not (0 < w <= 1 and 0 < h <= 1 and x-w/2 >= -1e-6 and y-h/2 >= -1e-6 and x+w/2 <= 1+1e-6 and y+h/2 <= 1+1e-6):
                    raise ValueError(f'Box out of bounds: {label}')
                class_counts[int(cls)] += 1
        extra = set(label_root.rglob('*.txt')) - expected_labels
        if extra:
            raise ValueError(f'Orphan labels in {label_root}')
        counts[split] = dict(images=len(images), boxes_by_class=dict(zip(names, class_counts)))
        if split == 'train' and not all(class_counts):
            raise ValueError('Every declared class needs training boxes')
    if set(indexed) != seen_images:
        raise ValueError('Manifest has extra or unsupported image entries')
    return dict(root=str(root), classes=names, splits=counts,
                manifest_sha256=sha256(manifest), config_sha256=sha256(data),
                content_sha256=content_hash.hexdigest())
