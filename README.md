# AERIS-Rail

Modular research software for railway UAV inspection. **Simulation only:** no aircraft commands, trained image detector, or field safety claims.

Requires Python 3.10+; no external dependencies.

## Build the complete project

Start with the [complete project execution plan](docs/project_execution_plan.md). It covers UAV imagery, annotation, dataset splits, example YOLO image training/inference commands, where trained weights appear, image-backend implementation, SITL control, evidence integration, energy/docking, and evaluation. The [image dataset YAML](examples/image_detection/data.yaml) is a template only. The optional image commands require your real data and a separately installed vision framework; no trained image weights are included.

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

This trains a diagonal normality model on **numeric features**, calibrates a threshold on validation normals, evaluates held-out test records, and replays their scores through the mission. The bundled dataset is synthetic; its metrics do not establish railway detection performance. Image feature extraction and supervised defect detection are future implementations.

## Modules and guides

| Stage | Code | Current capability |
|---|---|---|
| Detection | `aeris/detection/` | Synthetic backend, trainable numeric normality baseline, evaluation/replay |
| UAV control | `aeris/control/` | Abstract corridor simulator and control interface |
| Coordination | `aeris/simulation.py` | Inspection orchestration and quality gate |
| Continuity | `aeris/mission.py`, `aeris/persistence.py` | Return-energy checks, coverage ledger, dock checkpoint |

Read the [implementation and training guide](docs/implementation_guide.md) for each stage's datasets, labels, training versus configuration, commands, module contracts, acceptance checks, and remaining implementation work. See the [doctoral research essay](docs/doctoral_research_essay.md) for hypotheses and experimental design.

The model uses one dock and constant travel cost. Geometry can make distant coverage infeasible. Charging and docking are discrete events without physical dynamics. Checkpoints do not identify the detector: offline replay resumption requires reinjecting the same backend as described in the guide. PX4/ArduPilot SITL and physical aircraft integration are not included.
