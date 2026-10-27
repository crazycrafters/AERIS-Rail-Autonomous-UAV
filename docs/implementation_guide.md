# AERIS-Rail implementation and training guide

For a complete ordered action plan, image-label examples, optional YOLO training commands, and deliverables, start with the [project execution plan](project_execution_plan.md).

## 1. What exists and what comes next

The repository implements a simulation-first development path. All commands below run from the repository root using Python 3.10 or newer. No external Python packages, services, GPU, secrets, or aircraft are required for the implemented examples.

| Stage | Implemented now | Next implementation |
|---|---|---|
| Detection | Synthetic detector, feature-based normality training/evaluation, offline replay | Licensed imagery, image encoder, asset segmentation, supervised defect model |
| UAV control | Abstract corridor simulator and control interface | PX4 or ArduPilot software-in-the-loop adapter, pose and camera simulation |
| Coordination | Quality gate, review flag, contiguous evidence coverage | Timestamp/pose association, camera actions, bounded recapture policy |
| Continuity | Return-energy supervisor, simulated dock/charge, versioned dock checkpoint | Learned/calibrated return estimator, event journal, dock failure handling |
| Physical evaluation | No aircraft interface | Independently reviewed supervised closed-course trials |

Training a defect model is different from tuning a controller, calibrating an energy estimator, or testing a state machine. Do not invent a training dataset for a deterministic component that needs specification and tests instead.

## 2. Module map and execution flow

```text
aeris/config.py              mission parameters and validation
aeris/detection/__init__.py  Detector contract and SyntheticDetector
aeris/detection/offline.py   feature dataset, NormalityModel, replay adapter
aeris/detection/__main__.py  train / evaluate / replay commands
aeris/control/__init__.py    UAV contract and SimulatedUAV
aeris/mission.py             EnergySupervisor and CoverageLedger
aeris/persistence.py         checkpoint serialization
aeris/simulation.py          stage coordinator (Simulator)
aeris/__main__.py            synthetic mission command
```

The coordinator asks the energy supervisor whether the next acquisition is feasible, advances the simulated vehicle, requests an observation from the detector, and advances the ledger only for an accepted-quality observation. An anomaly raises a review flag; it does not certify a defect and does not authorize flight maneuvers. On return the vehicle docks and the coverage checkpoint is saved. One-segment overlap is acquired after resumption.

`Config` and `Simulator` remain importable from `aeris.simulation` for compatibility. A detector can be injected with `Simulator(config, detector=backend)`. `Detector.observe(segment)` returns `segment`, `quality_ok`, `known_score`, `anomaly_score`, and `review_required`; additional evidence metadata is allowed. The offline anomaly score is an unbounded standardized distance, whereas synthetic fixture scores lie in [0,1]. Consumers must use the backend's decision and threshold rather than treating all scores as probabilities or comparing thresholds across backends. `known_score=0` in offline mode means no supervised model is implemented.

## 3. Run the implemented workflow

```sh
python -m unittest discover -s tests -v
python -m aeris --seed 27 --output outputs/demo
python -m aeris --seed 27 --max-sorties 1 --output outputs/interrupted
# The preceding command deliberately exits 2: sortie limit, incomplete coverage.
python -m aeris --resume outputs/interrupted/checkpoint.json --output outputs/resumed

python -m aeris.detection train --data examples/features.jsonl --model outputs/normality.json
python -m aeris.detection evaluate --data examples/features.jsonl --model outputs/normality.json
python -m aeris.detection replay --data examples/features.jsonl --model outputs/normality.json --output outputs/offline
```

The bundled feature dataset is synthetic and intentionally easy. Perfect metrics on its four test examples establish command integration only. They are not evidence of railway detection performance. Mission JSON contains review candidates and evidence IDs. A missing observation or bad-quality observation prevents coverage from advancing. Repeated deterministic quality failure terminates as `image_quality_blocked`; additional sorties do not fabricate better imagery. `energy_infeasible` means the configured geometry/energy budget cannot advance. Simulated charging resets energy at the next launch without modeling charging time.

## 4. Stage 1 — detection data and training

### Collect and label imagery

Use licensed railway imagery or authorized acquisitions. Begin with a small, precise asset scope such as visible fasteners; do not label invisible internal cracks as observable RGB defects. Record image ID/path, license, site, collection day, timestamp, physical asset/segment ID, camera calibration, altitude, viewing angle, exposure, weather, and positioning uncertainty. Capture normal appearance across lighting, wet surfaces, shadows, wear, occlusion, and different track materials.

Annotate asset boxes or masks, visible known defect classes, verified healthy assets, ambiguous observations, and image quality. A qualified review process must define defect confirmation and disagreement resolution. Keep uncertain labels out of healthy training examples. Near-duplicate frames and repeated views of the same asset must remain in the same split.

Reserve whole sites for validation and test, with day/asset grouping inside each partition. Freeze the test manifest before fitting models. Unknown-category experiments require withholding entire anomaly categories from training and threshold selection. The supplied loader checks site separation and unique IDs; it cannot detect duplicated images under different IDs, validate licenses, or determine annotation correctness.

### Train the implemented feature baseline

Extract one fixed-length vector per asset crop using a fixed image encoder or explicitly defined descriptors. The encoder is not included here. Fit normalization/PCA, if used, on training data only and store its parameters with the encoder version. Use identical preprocessing during evaluation and inference. Do not use ground-truth defect labels or synthetic truth as features.

Write one JSON object per line, following this schema:

```json
{"id":"asset-0001-view-1","site":"site-A","day":"2026-10-01","split":"train","segment":0,"label":"normal","quality_ok":true,"features":[0.12,0.34]}
```

Required fields are `id`, `site`, `split`, `segment`, `label`, `quality_ok`, and `features`. `day` is recommended metadata and is not validated by this loader. Splits are `train`, `validation`, and `test`; labels are `normal` and `anomaly`. Features must be finite and share a dimension. Segment IDs are nonnegative integers. Replay additionally requires exactly one test record for each contiguous segment starting at zero; training/evaluation allow multiple records per segment.

Run `train` and `evaluate` as above with your feature manifest. The baseline fits a mean and per-dimension standard deviation using accepted-quality training normals only. It scores the root mean square standardized distance. A 1e-6 scale floor handles constant dimensions; it is numerical protection, not evidence that a constant feature generalizes. Highly correlated embeddings violate the diagonal approximation. Consider regularized covariance, nearest neighbors, or PatchCore after establishing this baseline.

The threshold is the empirical (1 - false-alarm-rate) quantile of accepted validation normals. Change the target with `--false-alarm-rate 0.05`. Decisions use score strictly greater than threshold. Small validation sets, ties, and distribution shift mean this is not a guaranteed future false-alarm rate. Validation anomalies can inform a separately declared tuning protocol, but are unused by the implemented trainer. Test records are never used for fitting or threshold selection.

The evaluator uses accepted-quality test normals and anomalies and reports TP, FP, TN, FN, precision, recall, false-positive rate, and quality rejection count. Precision is null when no positive predictions exist. It rejects empty or single-class accepted test sets. Extend evaluation to PR curves, uncertainty intervals grouped by site, false alerts per kilometer, and unknown-class recall before research claims.

### Implement image-based models next

1. Build a dataset adapter that loads image crops and asset metadata from the frozen manifest. Add malformed-image and missing-calibration handling.
2. Establish an asset localization model (boxes or segmentation). Train with asset annotations; preserve image resolution sufficient for the smallest target component.
3. Fine-tune a supervised detector for named visible defects. Choose a maintained framework, pin its versions, record pretrained-weight license and checksum, and save training configuration and seed. No specific framework or GPU stack is installed by this repository.
4. Train a separate normality model on confirmed healthy crops. Use the existing numeric baseline first; compare a stronger embedding/patch method later.
5. Calibrate fusion on validation data and evaluate on untouched sites and unknown categories. Include blur, shadows, and wet surfaces as nuisance conditions.
6. Implement `Detector.observe` around the image pipeline, including quality checks, evidence ID, timestamp, location uncertainty, and backend-specific review decisions. Add replay fixtures before real-time integration.

For every model release save data-manifest hashes, preprocessing version, encoder/weights identity, feature dimension, labels, split definitions, threshold selection procedure, and evaluation report. The small baseline JSON currently stores only its numeric parameters and format version; production provenance is future work.

## 5. Stage 2 — UAV control and simulation

### Data and training requirements

Conventional autopilot stabilization and waypoint following do not require training a neural network on railway defect images. Configure and validate the autopilot and navigation stack first. Required inputs are a permitted corridor centerline, coordinate frame and origin, altitude reference, geofence, landing location, vehicle parameters, sensor calibration, and contingency specification.

Visual railway localization, if added, is a separate learned component: train rail/track segmentation from masks, evaluate lateral/heading error against independent pose truth, and include parallel tracks, switches, shadows, and track disappearance. Train/test geographic separation applies here too. A visually plausible track is not proof of correct branch identity.

### Implementation path

`SimulatedUAV` currently tracks only an integer corridor boundary and abstract energy. Its `UAV` protocol is a target abstraction, not a complete flight adapter. It exposes launch, movement, inspection advance, and dock actions. There is no arming command, network transport, geographic route follower, obstacle avoidance, or flight dynamics.

Choose **one** autopilot for the next milestone: PX4 SITL or ArduPilot SITL. Use its official installation instructions for a pinned release and compatible simulator; do not mix incompatible simulator/ROS distributions. This guide does not claim those tools are installed or tested.

Before writing an adapter, define asynchronous commands and telemetry: request ID, timestamp, pose frame, mission state, acknowledgement, timeout, cancellation, and completion criteria. Replace the simulator's synchronous assumptions with a state machine. Add simulated pose and camera streams, then demonstrate waypoint following without perception. Test return, landing failure, stale telemetry, lost localization, and failed acknowledgements. Only after those pass connect rail-image localization as a complementary signal.

Acceptance should use lateral/heading errors, geofence violations, lost-track detection, successful contingency transitions, and route completion. Set numerical limits from vehicle/sensor requirements before experiments. A PID tuning exercise or a stable hover does not validate railway inspection.

Reinforcement learning and imitation learning are optional research alternatives, not prerequisites. They require independently specified training environments, held-out scenarios, reward audits, and an external supervisor. They are not implemented here.

## 6. Stage 3 — connect detection to the mission

### Data requirements

Acquire synchronized image timestamps, pose and pose uncertainty, camera intrinsics/extrinsics, gimbal state, segment/asset associations, quality labels, and inspection decisions. Clock offsets and coordinate transforms must be measured. A high detector score at the wrong asset location is an inspection failure.

### Implement and validate

The current coordination layer accepts a quality flag, records detector outputs, and advances contiguous coverage. Missing or bad data does not advance the ledger. Use `python -m aeris.detection replay ...` to exercise trained feature scores through this path.

Next, replace integer lookup with a timestamped capture/evidence service. A capture is accepted only when required asset regions, position confidence, resolution, and image quality satisfy declared criteria. Add a bounded recapture policy with explicitly permitted speed/camera adjustments; all actions must pass flight and energy constraints. Retain unresolved segments rather than counting elapsed distance as inspected distance.

No neural training is needed for this coordinator unless you deliberately introduce a learned policy. Quality classifiers need labeled blur/exposure/occlusion examples; geometric resolution and timestamp checks can be deterministic. Test delayed inference, missing frames, contradictory scores, duplicate evidence, and image-to-pose misalignment. Verify that an anomaly review flag never bypasses the supervisor.

## 7. Stage 4 — energy management, docking, and continuation

### Data and optional model fitting

The existing energy model is deterministic: distance × cost × fixed wind multiplier, plus inspection cost. It needs configured parameters, not a training run. The planner and simulated world share that model, so reserve tests cannot establish prediction accuracy.

For a real estimator collect time-aligned voltage/current integration, usable battery capacity, state of charge, state of health, payload, speed, altitude changes, wind estimate, temperature, distance, and actual return consumption. Partition by flight session and battery, keeping a later-condition test set. Fit a simple physical/regression baseline before more complex models. Calibrate conservative residual bounds on validation flights and report underprediction and reserve violations on held-out flights. This fitting pipeline is not yet implemented.

### Implementation and validation

`EnergySupervisor` checks inspection energy plus return plus reserve and uncertainty margin. It also rejects a resume boundary that cannot be safely reached and returned from within its abstract model. `CoverageLedger` prevents skipping an unverified segment. Dock checkpoints store configuration and contiguous verified coverage; format version 1 remains compatible with the earlier simulator.

Checkpoints do not store the detector/model identity, raw evidence, charging authorization, historical events, or an in-flight position. When resuming a synthetic mission, use `python -m aeris --resume ...`. For an offline replay checkpoint, reconstruct the same `FeatureReplayDetector` and call `Simulator.load(path, detector=detector)` in Python; the synthetic CLI does not restore offline detector state and must not be used to resume offline experiments. Keep the original dataset and model artifacts with each run.

Next add a transactional evidence journal, backend/model provenance, idempotent replay, and recovery at each acquisition boundary. Add states for dock unavailable, landing failed, charging failed, battery maintenance, and denied relaunch. A dock event in this simulator is not an automatic landing implementation. Resume after verified charging and authorization should be an explicit transition, not an assumption of infinite operation.

Test insufficient capacity, unreachable remote segments, biased return estimates, interrupted writes, stale checkpoints, repeated observations, and changed model versions. Compare predictive return against fixed-charge thresholds on paired scenarios and compare checkpointed missions against restart-from-zero under equal budgets.

## 8. Stage 5 — supervised physical evaluation

This is an integration and validation phase, not a model-training shortcut. Begin only after the simulator acceptance criteria and operating approvals are established. Use a qualified operator and an authorized closed course. Start with vehicle-only checks, then passive image recording, offline inference, and operator-reviewed mission suggestions. Progression to automated mission requests needs a separately validated control integration.

Keep an independent inspection reference and measured flight telemetry. Field imagery may become future training data only after annotation and split assignment; do not continually tune on the same final evaluation route and call it a held-out test. Internal rail defects remain outside the certification scope of RGB inspection.

## 9. Completion checklist for the next development milestone

- Choose the first visible asset/defect classes and document annotation criteria.
- Obtain a licensed image dataset with site-separated train/validation/test manifests.
- Implement and version the image-to-feature adapter; run the existing normality baseline.
- Add supervised image detection and evaluate it against the baseline.
- Select PX4 or ArduPilot and verify vehicle-only SITL following and contingencies.
- Add timestamped evidence association and bounded recapture.
- Replace dock-only coverage JSON with an evidence-linked durable journal.

Only the standard-library simulation, numeric baseline, and supplied synthetic examples are verified in this repository. Image-model training, SITL, physical docking, and field operation remain explicit future milestones.
