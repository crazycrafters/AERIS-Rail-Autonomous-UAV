"""Versioned dock checkpoints; not a flight journal or concurrent database."""
from dataclasses import asdict
import json
from pathlib import Path
from .config import Config
from .mission import CoverageLedger


def save_checkpoint(path, config, covered):
    CoverageLedger(config.segments, covered)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(dict(version=1, config=asdict(config), covered=covered), indent=2))
    temp.replace(path)


def load_checkpoint(path):
    data = json.loads(Path(path).read_text())
    if data['version'] != 1:
        raise ValueError("Unsupported checkpoint version")
    config = Config(**data['config'])
    CoverageLedger(config.segments, data['covered'])
    return config, data['covered']
