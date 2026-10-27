# AERIS-Rail: complete project execution plan

This guide explains what you must obtain, what to implement, how to train the image models, and what evidence is required before moving to the next stage. It is a development plan, not a claim that those stages are already implemented. The immediate goal is **offline detection from UAV railway images**. Aircraft integration follows only after that works.

## Implementation update

The executable [implementation guide](implementation_guide.md) is now the command reference. `aeris/vision/` implements dataset auditing, YOLO training to `best.pt`, evaluation, still-image inference, embedding extraction and evidence replay. `aeris/report.py` exports a static report. Optional PX4 SITL scripts are provided but not flight-validated. The sections below retain the broader project/research plan; use the implementation guide for current code paths.

## 1. Start here: repository status and first objective

The current code has a working abstract mission simulator and a trainable normality baseline for numeric feature vectors. It now has optional image embedding extraction, a YOLO training/inference wrapper and static reports. It does **not** include trained railway image weights, a live camera driver, ROS 2 integration, validated real-time flight coupling, a review database, or physical docking control.

The existing `aeris/detection/offline.py` is not the model to train directly on images. An image-based model must be trained with the optional vision framework and your imagery; use `aeris.vision` as documented in the implementation guide. The direct framework commands below are baseline planning examples; the newer wrapper was smoke-tested separately on generated geometry, not railway data. The supplied YAML is a template, not a dataset.

First produce this artifact chain:

```text
licensed UAV imagery + asset definitions
  → reviewed annotations + frozen site-separated manifest
  → trained image detector + validation-selected operating threshold
  → held-out image evaluation + error review
  → offline inspection records linked to image evidence
  → mission replay with coverage and energy constraints
  → autopilot software-in-the-loop integration
  → independently evaluated closed-course system
```

Do not start by buying a dock or training an end-to-end flight policy. Resolve what your camera can see and what a useful detection means first.

## 2. Decide the initial inspection scope

Use visible fastener presence/absence as a suggested first experiment, **only if the available imagery resolves fastener slots**. Do not assume this class choice is correct for every aircraft camera or railway. If it is not observable, start with larger visible assets or obstructions instead.

Write a one-page scope specification with:

- Asset type, railway/component variants, and defect definitions confirmed by an asset specialist.
- Required output: image/asset ID, class, bounding box, score, capture time, approximate location and uncertainty, quality status, and human review decision.
- Smallest visible feature, desired ground resolution, allowed viewing angles, and acceptable blur/occlusion.
- Operating conditions included and excluded from the first experiment.
- Evaluation targets: per-class recall, false alerts per inspected kilometer, review workload, asset-localization error, latency, and the definition of complete acquisition.
- Which classes are held out as unknown anomalies for a later experiment.

Set acceptance targets before reviewing test results. No universal mAP or confidence cutoff establishes railway inspection adequacy. Keep an `uncertain/not_observable` annotation state; do not force it into healthy or defective labels.

**Deliverable:** `scope-v1.md` and a reviewed class/annotation handbook. Class names in the supplied YAML are examples until this decision is complete.

## 3. Resources and hardware decisions

| Component | What you need initially | What to record |
|---|---|---|
| Imagery | Licensed UAV photos/video or authorized closed-course captures | License, site, date, collection method, intended use |
| Annotation | A box/mask tool such as CVAT or Label Studio and a qualified reviewer | Tool/export version, class map, reviewer disagreements |
| Training | A Python environment; NVIDIA GPU optional but usually useful | OS, Python, framework, CUDA/driver and GPU memory |
| Camera study | Original-resolution images and camera metadata | Intrinsics, focal length, sensor dimensions, exposure, altitude, gimbal pose |
| Flight simulation | One selected autopilot and a compatible simulator | Exact versions, vehicle model, sensor rates, coordinate frames |
| Storage | Immutable raw-data store plus versioned manifests and model artifacts | Checksums, retention, access rules, backup policy |

CPU training can verify plumbing on a small subset but may be impractical for full experiments. Start with a small model, batch size that fits memory, and a measured throughput trial before committing to a long run. Do not choose a GPU or budget from an unmeasured estimate. Record annotation, review, storage, training, and operator effort separately.

The first offline stage needs no UAV connection and no dock. A flight platform should be selected later based on payload, camera resolution, flight time, autopilot interfaces, and approved test conditions.

## 4. Collect images that can support the task

### 4.1 Check resolution before collecting thousands of frames

For an approximately nadir view over locally planar ground:

```text
GSD (meters/pixel) ≈ height_above_ground × sensor_width / (focal_length × image_width_pixels)
feature_width_pixels ≈ feature_width_meters / GSD
motion_blur_pixels ≈ ground_speed × exposure_seconds / GSD
```

Use consistent length units for sensor width and focal length. For illustration, a 0.02 m feature at 0.005 m/pixel spans only four pixels before blur or compression. That may be inadequate; verify on reviewed crops rather than assuming a model can recover missing detail. Oblique views, rolling shutter, terrain, distortion, and stabilization require a fuller camera model. Choose acquisition geometry with the operator based on actual test imagery.

### 4.2 Preserve metadata and raw data

Keep original imagery read-only. Assign stable image IDs and SHA-256 hashes. Record site, track/asset identifiers, collection session/day, timestamps and clock source, camera calibration/version, resolution, exposure, position and uncertainty, altitude reference, camera pose, weather, and license. Use null for unavailable metadata; never invent accurate coordinates.

Sample video by spatial novelty and image quality, not by treating every adjacent frame as independent data. Keep enough sequence information for future multi-frame corroboration. Include difficult healthy cases: wet rails, rust, shadows, vegetation, glare, different fastener designs, partial views, and motion blur. Defect examples require independent confirmation where possible.

**Deliverable:** raw-data inventory and a manifest with stable IDs, hashes, metadata, annotations, and split assignment.

## 5. Annotate and split the dataset

### 5.1 Annotation policy

For `fastener_present`/`fastener_missing`, annotate a consistent expected **fastener slot region**, including the location where the component would have been. Absence has no physical object to outline; random boxes around empty background teach an inconsistent task. Document slot geometry with examples. If slot location cannot be established from context, mark unobservable rather than missing.

If slot labeling is unreliable, use a two-stage alternative: detect sleeper/rail-seat regions first, then classify each aligned slot crop as present/missing/uncertain. Define which configuration is in scope; track designs with different fastener layouts need separate handling.

Annotate every visible in-scope asset in each selected image. Unlabeled in-scope objects can be incorrectly treated as background. Include reviewed negative images and empty YOLO label files where no in-scope assets exist. Do not use empty labels to hide incomplete annotation. Keep ambiguity and quality metadata in the manifest even though YOLO box files cannot represent it directly.

Have a second reviewer check a subset covering every class and condition. Reconcile disagreements, document them, and revise the handbook before finalizing labels. Zooming an unreadable image does not create ground truth.

### 5.2 Split before augmentation or frame extraction leaks

Group all views of the same physical asset, video/session, and nearby duplicates together. Reserve whole sites for validation and test where possible. A 70/15/15 allocation by groups is a planning example, not a requirement or a substitute for sufficient independent defect examples. If only one site is available, use separated contiguous sections and sessions, disclose the limitation, and obtain an external site before claiming site generalization.

Keep the test set locked. Use training data for fitting; validation for hyperparameters, threshold selection, and early stopping; test once for the final selected model. Create a separate held-out anomaly-category protocol for unknown detection. Do not rebalance or augment validation/test images to make metrics look better.

### 5.3 YOLO directory and label format

Create your dataset outside Git, for example:

```text
/workspace/datasets/aeris-rail/
  images/train/siteA_0001.jpg
  images/val/siteB_0001.jpg
  images/test/siteC_0001.jpg
  labels/train/siteA_0001.txt
  labels/val/siteB_0001.txt
  labels/test/siteC_0001.txt
```

Each line in a label file is:

```text
class_id center_x center_y width height
0 0.50 0.40 0.08 0.06
```

Coordinates are normalized by image width/height and must describe a nonzero box inside the image. IDs must match the zero-based mapping in [the YAML template](../examples/image_detection/data.yaml). Image/label stems must match. Store image/asset identity and defect-confirmation details in the manifest, not in class IDs.

Before training validate decodability, dimensions, missing/extra labels, class ranges, box bounds, duplicate hashes, site/asset overlap between splits, and annotation completeness. Visually render a stratified sample of exported labels. The validator is now implemented as `python -m aeris.vision validate`; see the implementation guide for its manifest and accepted layout.

## 6. Train the supervised image detector

### 6.1 Select a reproducible baseline

Use a small pretrained YOLOv8 detector as a concrete starting baseline in the Ultralytics framework. `yolov8n.pt` is a suggested architecture/initialization, not a trained railway model and not a claim that it is the best model. Check software, pretrained-weight, and dataset licenses against your intended distribution before adopting them. The framework may download weights when first used. Preserve HTTPS/checksum verification and record artifact origin/hash.

These are **external-framework commands**, not existing `aeris` commands. They require your real dataset, network access to the package/weight sources, and a compatible installed environment. Version compatibility must be validated on the target machine; no framework version is certified by this documentation.

### 6.2 Prepare an isolated training environment

Example shell commands, from the repository root:

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install ultralytics
mkdir -p outputs/image-training-environment
python -m pip freeze > outputs/image-training-environment/requirements-resolved.txt
python -c "import torch, ultralytics; print('torch', torch.__version__); print('ultralytics', ultralytics.__version__); print('cuda', torch.cuda.is_available())"
```

The unpinned installation is for establishing the first compatible environment. Freeze and review the resulting versions, then reproduce subsequent experiments using those resolved dependencies and a recorded base environment. CUDA-enabled PyTorch installation must follow its official selector for the actual driver/platform; do not guess a CUDA wheel. Never run `pip freeze` from a credential-bearing package URL without reviewing/redacting credentials before sharing the result.

The standard-library repository tests still run without this optional environment. Do not replace the lightweight core with mandatory GPU dependencies.

### 6.3 Configure data and run a short smoke experiment

Copy `examples/image_detection/data.yaml` to a local working configuration such as `outputs/data-local.yaml`. Change its `path` and reviewed class names to match your data. Do not commit a machine-specific absolute path as a universal default.

Example CPU smoke command:

```sh
yolo detect train model=yolov8n.pt data=outputs/data-local.yaml epochs=1 imgsz=640 batch=2 device=cpu workers=0 seed=27 project=outputs/image_detector name=smoke
```

Inspect actual label overlays, batch visualizations, loss output, class counts, and resulting validation artifacts. One epoch tests data flow; it does not produce a validated detector. If training reports corrupt or unlabeled data, fix the manifest/export rather than suppressing the warning.

### 6.4 Run the baseline training experiment

Example starting configuration, to adjust after measuring memory and feature resolution:

```sh
yolo detect train model=yolov8n.pt data=outputs/data-local.yaml epochs=100 imgsz=1024 batch=4 device=0 workers=2 seed=27 project=outputs/image_detector name=baseline
```

`device=0` requires a suitable GPU; use `device=cpu` only if the measured runtime is acceptable. The epoch count and image size are starting hyperparameters, not established best settings. Choose run names that do not already exist; framework output-directory suffixes can otherwise change artifact paths. Record the actual run directory.

For tiny assets, inspect their size **after resizing**. Consider high-resolution tiles with overlap and coordinate reconstruction, or an asset detector plus crop classifier. Split by site/asset before generating tiles so neighboring crops cannot leak across splits. Include border cases and normal context. Larger input size alone cannot fix information absent in the original image.

Use only plausible augmentations. Aggressive geometric transformations, synthetic missing components, and pasted defects can introduce shortcuts. Document augmentation choices and compare with a conservative baseline. Tune only on validation data. Repeat selected experiments across predeclared seeds and report variability rather than selecting the luckiest run.

### 6.5 Locate the model you trained

For a successful run whose actual directory is `outputs/image_detector/baseline`, the framework normally writes:

```text
outputs/image_detector/baseline/weights/best.pt
outputs/image_detector/baseline/weights/last.pt
```

`best.pt` is selected using the framework's validation criterion; `last.pt` is the latest saved training state. Confirm actual outputs and selection semantics for your pinned framework. **No trained railway weights are included. A synthetic smoke test produced local ignored weights only.** These are the image-model weights you will obtain after training on your dataset. Keep them in versioned artifact storage, not ordinary Git. Record SHA-256 hashes and the run/data configuration beside them.

## 7. Evaluate, choose a threshold, and run image inference

Run validation first to choose an operating point with the required review budget. Then evaluate the selected model on the locked test split:

```sh
yolo detect val model=outputs/image_detector/baseline/weights/best.pt data=outputs/data-local.yaml split=test imgsz=1024 device=0 project=outputs/image_detector name=test-report
```

Report per-class precision/recall and AP, missed defects, false alerts, small-feature performance, and quality rejection rate. Group uncertainty by site/session rather than treating correlated frames as independent samples. Image metrics alone cannot establish false alarms per kilometer; that requires spatially aligned route coverage and deduplication. Keep reviewer-confirmed defect findings separate from model candidates.

Set the inference threshold using validation outcomes. The following command illustrates inference with an example threshold of 0.25, **not a recommended operational threshold**:

```sh
yolo detect predict model=outputs/image_detector/baseline/weights/best.pt source=/workspace/datasets/aeris-rail/images/test conf=0.25 imgsz=1024 device=0 save_txt=True save_conf=True project=outputs/image_detector name=predictions
```

Review overlays and failure examples, including healthy unusual surfaces and unreadable frames. An empty prediction is not evidence that the asset was observed and healthy. It can mean no visible asset, missing localization, low score, or inadequate resolution. Add an explicit asset-presence/observability test before counting coverage.

**Gate:** a frozen evaluation report, error analysis, selected validation threshold, model hash, class map, dataset manifest hash, and measured inference latency on the intended device. If quality or defect recall is inadequate, improve acquisition/annotations first and run a new versioned experiment; preserve the old test protocol.

## 8. Implement the image inference backend in this repository

Earlier proposed file layout (actual implemented equivalents are in `aeris/vision/`; live capture/evidence services remain future work):

```text
aeris/detection/images.py           image decoding and preprocessing
aeris/detection/yolo_backend.py     pinned-framework adapter and result conversion
aeris/detection/dataset.py          image manifest and annotation validation
aeris/evidence.py                   typed capture/asset/evidence records
tests/test_image_detection.py       image fixtures and adapter integration tests
```

Implement a reusable image-inference function before wrapping `Detector.observe(segment)`. It should accept an image/evidence record and return multiple detections with original-image box coordinates, class IDs/names, scores, image quality, and model identity. Never discard the individual boxes into a single score in the only stored record.

A minimal external-framework API pattern is:

```python
from ultralytics import YOLO

model = YOLO("outputs/image_detector/baseline/weights/best.pt")
results = model.predict(source="capture.jpg", conf=0.25, imgsz=1024)
for result in results:
    for box in result.boxes:
        class_id = int(box.cls.item())
        score = float(box.conf.item())
        xyxy = box.xyxy[0].tolist()
        # Persist these with image ID, dimensions, model hash and capture metadata.
```

This snippet is illustrative and requires trained weights and a real image. The threshold must be replaced by the validation-selected value. Load the model once per worker, not once per frame. Test output shapes and empty results against your pinned framework.

For offline mission replay, map each segment to reviewed image evidence using a manifest. The adapter should invoke image inference, verify asset visibility/quality, and return the existing contract (`segment`, `quality_ok`, `known_score`, `anomaly_score`, `review_required`) plus evidence IDs. Store full detections separately. Until an anomaly model exists, represent its absence explicitly in new evidence records rather than interpreting a fabricated zero as proof of normality.

Define error behavior for missing/corrupt images, unknown class IDs, wrong input scale, unavailable GPU, model-load failure, missing timestamps, and incomplete metadata. None of these may advance verified coverage silently. Unit tests should exercise error paths; a separate integration test should use the actual pinned model and licensed image fixture.

## 9. Add unknown-anomaly detection after the supervised baseline

YOLO recognizes its trained classes. It does not become an unknown-defect detector by lowering the confidence threshold.

1. Collect confirmed healthy asset crops covering expected normal variation.
2. Freeze a pretrained image encoder and crop/preprocessing rules; do not fit preprocessing on test data.
3. Extract numeric embeddings into the schema supported by `aeris/detection/offline.py`.
4. Train/evaluate the existing diagonal-normality baseline; this establishes a transparent reference.
5. Compare a stronger normality approach such as patch nearest-neighbor features with held-out sites and unknown categories.
6. Calibrate thresholds on validation normals and any explicitly allowed validation anomaly categories. Keep final unknown categories untouched.
7. Evaluate recall at a fixed false-alert/review budget; record nuisance causes and uncertainty.
8. Fuse supervised and anomaly evidence using a validation-defined rule, with quality gating and human review.

Do not interpret standardized distance or object confidence as calibrated defect probability. Repeated frames are correlated; multi-frame voting needs asset association and a measured false-alert effect. Normality also requires asset visibility: a missing fastener may be invisible to a pipeline that crops only successfully detected fasteners. Use expected slot geometry or a separate asset-localization stage.

## 10. Build UAV control using autopilot software-in-the-loop

### 10.1 Choose and pin a stack

A reasonable default is PX4 SITL with its documented compatible simulator; ArduPilot SITL is an alternative. Choose one first. Select the exact OS, autopilot release, simulator release, bridge/SDK, and optional ROS 2 distribution from official compatibility instructions. Save a reproducible dependency configuration after a successful installation. This repository does not currently install or launch any of them.

The autopilot handles low-level stabilization and vehicle failsafes. The inspection application supplies mission requests through a validated interface; a defect model should not output motor commands. Conventional route following needs configuration and testing rather than supervised image training. Visual track segmentation is an optional separate learned localization input.

### 10.2 Vehicle-only milestone

Before integrating perception:

- Load a synthetic corridor with a defined world origin and transform convention.
- Define geofence, altitude reference, route boundaries, landing point, and simulated vehicle properties.
- Implement telemetry ingestion with timestamp, freshness, pose uncertainty, battery state, and autopilot mode.
- Implement asynchronous mission requests with acknowledgements, timeout, cancellation, and completion criteria.
- Demonstrate route following, return and landing, operator intervention, and explicit handling of lost/stale localization and command failure.
- Measure cross-track error, heading error, geofence violations, contingency latency, and route completion.

Do not equate command acknowledgement with physical completion. Do not equate the current integer `position` with GPS coordinates. Document ENU/NED/local/global conversions, radians/degrees, height references, and clock domains, and test their transformations.

### 10.3 Camera and railway localization milestone

Add a simulated railway scene and synchronized camera images. Validate camera calibration and the image-to-ground transform using known simulator truth. If training rail segmentation, annotate track/rail masks and split by scene and physical site. Evaluate wrong-branch selection at switches and parallel lines, not only average segmentation overlap. Low track confidence should trigger a specified contingency rather than a guessed branch.

**Gate:** versioned simulator scenarios and evidence of correct vehicle-only and failure behavior before perception can request changes to the inspection mission.

## 11. Connect flight, camera and inspection evidence

Replace the synchronous simulator loop with an explicit asynchronous state machine. A proposed sequence is:

```text
PREFLIGHT → READY → TRANSIT → INSPECT
INSPECT → RETURN → LANDING → DOCK_VERIFIED → CHARGING → READY
INSPECT → PAUSED / CONTINGENCY when prerequisites degrade
```

Every transition needs preconditions, acknowledgement/completion evidence, timeout, and recovery. `READY` after charging must require verified battery/dock status and authorization, not simply a process restart. Unavailable dock and failed landing need independent contingency logic.

Define an evidence record containing image hash/URI, segment/asset ID, timestamp, pose and uncertainty, calibration hash, model hash, image quality, individual detections, anomaly score, review status, and acquisition acceptance. Store observation acceptance separately from a confirmed healthy/defective finding.

A proposed on-disk/DB separation is immutable images, append-only capture/decision events, and a transactional mission/coverage index. Use stable IDs and idempotent writes. On recovery, rebuild coverage from accepted evidence and detect missing files. Test power/process interruption between capture, upload, inference, evidence commit and coverage advancement.

Implement bounded recapture only after defining its allowed actions and energy checks. Poor imagery can justify another capture; it must not lead to unbounded flight or silently completed coverage. Measure end-to-end capture-to-decision latency and frame drops on the intended compute device.

## 12. Calibrate energy and implement dock continuity

The simulator uses abstract energy and symmetric travel with constant wind. Its planner knows the same cost model as the simulated world. Current reserve tests verify arithmetic, not realistic flight energy.

For measured energy use consistent units, for example:

```text
energy_Wh ≈ sum(voltage_V × current_A × interval_seconds) / 3600
continue only if usable_remaining_Wh >= action_Wh + return_Wh + reserve_Wh + uncertainty_margin_Wh
```

Obtain time-aligned telemetry with flight/session ID, battery ID and health, payload, speed, ascent, weather/wind, and actual return consumption. Account for sensor bias, unavailable capacity and temperature. Split estimator fitting by session/battery/conditions, calibrate residual margins on validation data, and evaluate underprediction on held-out flights. Maintain independent autopilot battery failsafes.

Test reachability from every proposed inspection point to an available approved landing location. More sorties cannot overcome a single dock's reachability limit. Compare alternate dock placement or shorter corridor assignments explicitly.

A physical dock requires a supported landing-localization solution, contact/charging verification, compatibility checks, weather/maintenance readiness, and failure modes. Use simulated states first; do not treat an SDK landing acknowledgement as verified charging. Add dock-unavailable and charge-failed scenarios before automating resume.

**Gate:** evidence-linked checkpoint restoration, no false coverage on failures, demonstrated multi-sortie completion in simulation, and measured energy-model error. Physical docking is a later engineering project.

## 13. Build a reviewer dashboard and reporting

Start after evidence schemas stabilize. The dashboard should show route/coverage state, unresolved segments, image evidence and asset location uncertainty, model version, anomaly queue, and reviewer decisions. Allow confirm/reject/uncertain with reason and audit history. Deduplicate repeat sightings of the same asset without discarding evidence.

Use a small local database first; add geospatial storage and object storage when scale justifies them. Authenticate access before exposing real infrastructure imagery. Record model changes so an old review is not silently reinterpreted by a new model. Do not present an unreviewed alert as a confirmed infrastructure defect.

## 14. Validate the research claims

| Question | Comparison | Required outcomes |
|---|---|---|
| Navigation fusion | Waypoints vs vision-only simulation vs fusion | Cross-track/heading errors, wrong branches, interventions |
| Unknown retrieval | Known-only vs anomaly-only vs combined | Recall at matched false-alert budget, site-held-out uncertainty |
| Energy planning | Fixed charge threshold vs predictive return | Reserve violations **and** completed coverage/abort rate |
| Continuity | Restart-from-zero vs checkpointed continuation | Unique verified distance, duplicates, energy/sortie budget |
| Temporal comparison | Single capture vs registered historical evidence | Nuisance alerts at matched recall, registration error |

Predeclare scenarios, acceptance criteria, statistical units, thresholds and exclusions. Use paired exogenous conditions where possible. Report failures and incomplete runs, not only successful missions. Keep software smoke-test outcomes separate from perception research results and physical safety evidence.

## 15. Supervised field progression

After simulation and review, use an authorized closed course with qualified personnel. Establish railway and aviation permissions appropriate to the location and operation. Progress through vehicle-only checks, passive image recording, offline model evaluation, operator-reviewed inspection suggestions, and only then separately validated mission automation. Train interaction, catenary clearance, GNSS degradation and emergency contingencies require explicit operational treatment.

Keep a truly independent evaluation set for the final trial. Do not repeatedly tune on the same route and claim field generalization. RGB inspection does not replace methods for internal rail defects.

## 16. Ordered backlog and deliverables

| Order | Action | Deliverable / completion evidence |
|---|---|---|
| 1 | Review asset scope and observability | Scope document, sample crops, accepted annotation rules |
| 2 | Obtain licensed data and metadata | Raw inventory, manifests, site/session groups |
| 3 | Annotate and audit splits | Reviewed YOLO dataset, duplicate/leakage checks |
| 4 | Implement image dataset validator | Failing fixtures and a successful real-dataset audit |
| 5 | Install/pin vision stack and train baseline | Environment record, logs, actual `best.pt`, model hash |
| 6 | Evaluate and select review threshold | Locked test report, error examples, latency measurements |
| 7 | Implement image backend and evidence export | Image → boxes/quality/evidence integration test |
| 8 | Add healthy-feature/unknown baseline | Encoder version, normality artifact, held-out anomaly report |
| 9 | Establish vehicle-only SITL | Pinned stack, route and contingency scenario results |
| 10 | Integrate camera/pose/inspection | Timestamp/transform checks and evidence-linked coverage |
| 11 | Add durable journal and energy calibration | Crash recovery tests, reserve/reachability comparisons |
| 12 | Add dock simulation and reviewer interface | Failed-dock/charge recovery, review audit trace |
| 13 | Conduct supervised closed-course evaluation | Independent inspection and telemetry report |

Start with orders 1–3. The information you need to supply is **representative licensed UAV imagery, target asset/defect definitions, collection metadata, and the available training hardware**. Without those, code can validate a pipeline but cannot produce meaningful railway model weights.

## 17. Artifact and repository hygiene

Commit source, small synthetic fixtures, reviewed schemas, template configurations, and documentation. Keep raw imagery, `.venv`, trained `.pt`/ONNX artifacts, and run outputs out of ordinary Git. Use a model registry or access-controlled object storage for large artifacts, with hashes/version references committed alongside evaluation summaries. A Git commit does not preserve external data automatically.

The current lightweight workflow remains available:

```sh
python -m unittest discover -s tests -v
python -m aeris --seed 27 --output outputs/demo
python -m aeris.detection train --data examples/features.jsonl --model outputs/model.json
python -m aeris.detection evaluate --data examples/features.jsonl --model outputs/model.json
python -m aeris.detection replay --data examples/features.jsonl --model outputs/model.json
```

These run on synthetic data without installing the optional image stack. For additional details of existing interfaces and checkpoint limitations, read [the implementation guide](implementation_guide.md). For hypotheses and research methodology, read [the doctoral essay](doctoral_research_essay.md).

## 18. Official documentation starting points

Use the documentation for the exact version you select. These links are reference starting points; no current compatibility matrix or installation was verified during this documentation update.

- Ultralytics detection training and dataset format: https://docs.ultralytics.com/tasks/detect/ and https://docs.ultralytics.com/datasets/detect/
- PyTorch installation selector: https://pytorch.org/get-started/locally/
- CVAT documentation: https://docs.cvat.ai/
- PX4 simulation: https://docs.px4.io/main/en/simulation/
- ArduPilot SITL: https://ardupilot.org/dev/docs/sitl-simulator-software-in-the-loop.html
- ROS 2 distributions: https://docs.ros.org/en/rolling/Releases.html
