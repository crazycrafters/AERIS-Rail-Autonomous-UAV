# AERIS-Rail

Modular research software for railway UAV inspection. **Research prototype:** local image training/inference and abstract mission simulation. No pretrained railway weights or validated physical-flight/dock integration are included. Optional PX4 SITL scripts are not flight-validated.

The core simulator requires Python 3.10+ with no external dependencies. The optional image stack is tested on Python 3.12; see `requirements-vision.txt`.

## Build the complete project

Start with the [complete project execution plan](docs/project_execution_plan.md). It covers UAV imagery, annotation, dataset splits, example YOLO image training/inference commands, where trained weights appear, image-backend implementation, SITL control, evidence integration, energy/docking, and evaluation. The [image dataset YAML](examples/image_detection/data.yaml) is a template only. The optional image commands require your real data and a separately installed vision framework; no trained image weights are included.

## Train an image detector after annotation

Follow the [step-by-step implementation guide](docs/implementation_guide.md), including environment installation, annotation manifest and dataset audit. Then run, adjusting your dataset path:

```sh
python -m aeris.vision configure --root /absolute/path/to/aeris-data --names fastener_present fastener_missing --output outputs/data-local.yaml
python -m aeris.vision train --data outputs/data-local.yaml --manifest /absolute/path/to/aeris-data/manifest.csv --model yolov8n.pt --epochs 100 --imgsz 1024 --batch 2 --device cpu --output outputs/rail-baseline
```

Trained weights: **`outputs/rail-baseline/fit/weights/best.pt`**. The wrapper prints the actual path/hash and writes provenance. Evaluation, still-image inference, embedding extraction, evidence replay and report commands are in the guide. Real labeled imagery is required to train a meaningful railway model.

## Run and test

```sh
python -m unittest discover -s tests -v
python -m aeris --seed 27 --output outputs/demo
python -m aeris --resume outputs/demo/checkpoint.json --output outputs/resumed
```

The CLI writes `mission.json` and an atomically replaced dock `checkpoint.json`. Exit 0 means complete coverage; exit 2 reports a blockage or sortie limit. Seed 27 demonstrates completion across two sorties; default seed 7 may block on poor imagery. Resume restores coverage with overlap, not historical events or an airborne vehicle state.

## Train and replay the feature baseline

```sh
python -m aeris.detection train --data examples/features.jsonl --model outputs/model.json
python -m aeris.detection evaluate --data examples/features.jsonl --model outputs/model.json
python -m aeris.detection replay --data examples/features.jsonl --model outputs/model.json --output outputs/offline
```

This trains a diagonal normality model on **numeric features**, calibrates a threshold on validation normals, evaluates held-out test records, and replays their scores through the mission. The bundled dataset is synthetic; its metrics do not establish railway detection performance. Optional image embedding extraction and supervised detector training/inference now live in `aeris/vision/`. This numeric baseline remains a separate anomaly model.

## Modules and guides

| Stage | Code | Current capability |
|---|---|---|
| Detection | `aeris/vision/`, `aeris/detection/` | Image training/evaluation/inference, embeddings, replay, numeric normality model |
| UAV control | `aeris/control/` | Abstract corridor simulator and control interface |
| Coordination | `aeris/simulation.py` | Inspection orchestration and quality gate |
| Continuity | `aeris/mission.py`, `aeris/persistence.py` | Return-energy checks, coverage ledger, dock checkpoint |

Read the [implementation and training guide](docs/implementation_guide.md) for each stage's datasets, labels, training versus configuration, commands, module contracts, acceptance checks, and remaining implementation work. See the [doctoral research essay](docs/doctoral_research_essay.md) for hypotheses and experimental design.

The model uses one dock and constant travel cost. Geometry can make distant coverage infeasible. Charging and docking are discrete events without physical dynamics. Checkpoints do not identify the detector: offline replay resumption requires reinjecting the same backend as described in the guide. PX4 SITL setup and optional telemetry/waypoint scripts are documented but not flight-validated. Real-time perception-flight coupling and physical dock integration remain unimplemented.
