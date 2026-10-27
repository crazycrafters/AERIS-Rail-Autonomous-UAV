# AERIS-Rail: step-by-step local implementation guide

This is the executable runbook. It starts **after you export annotations** and shows how to obtain `best.pt`, evaluate it, inspect new UAV images, replay evidence through mission logic, train an anomaly baseline, and prepare flight simulation. Commands invoke code committed in this repository unless labeled as external setup. Trained railway weights and private datasets are not included.

For collection geometry, annotation policy, research design, and acceptance criteria, also read the [project execution plan](project_execution_plan.md) and [doctoral essay](doctoral_research_essay.md).

## 0. What you can run and what was actually tested

| Step | Code provided | Verification in this change |
|---|---|---|
| Annotated image validation | `aeris/vision/dataset.py` | Valid datasets and failure cases tested |
| Image training → `best.pt` | `python -m aeris.vision train` | One CPU epoch on synthetic geometry; real weights produced |
| Image evaluation and prediction | `evaluate`, `predict` | Executed with those smoke weights |
| Embedding extraction and normality model | `features` + `aeris.detection` | Executed on synthetic images |
| Image evidence → mission replay | `replay` | Executed; quality/visibility gates tested |
| Mission report | `python -m aeris.report` | HTML export executed |
| Abstract control, battery, checkpoint resume | `python -m aeris` | Multi-sortie and recovery tests |
| PX4 SITL telemetry and waypoint scripts | `scripts/sitl_telemetry.py`, `scripts/px4_sitl_mission.py` | API construction/coordinate checks only; **not flown in SITL** |
| Real railway performance / physical dock | No validated flight/dock integration | Not implemented or tested |

The smoke detector produced zero detection accuracy after one epoch. Its weights prove the training/inference commands work, not that railway defects can be detected. No real imagery or trained railway model was available for evaluation.

For CPU/camera selection, flight-controller wiring, power and OS choices, read the [UAV hardware and connection guide](uav_hardware_and_connections.md) and fill in the [BOM worksheet](../examples/hardware/prototype_bom.csv).

## 1. Get the code and choose the local environment

Suggested environment: Linux with Python 3.11 or 3.12. The image workflow was exercised with Python 3.12, CPU PyTorch 2.5.1, torchvision 0.20.1, and the direct dependency pins in `requirements-vision.txt`. macOS/Windows installation and GPU execution were not validated here.

If you already cloned the repository, run `git pull` in your clean checkout. Otherwise:

```sh
git clone https://github.com/crazycrafters/AERIS-Rail-Autonomous-UAV.git
cd AERIS-Rail-Autonomous-UAV
python -m venv .venv
```

Activate on Linux/macOS:

```sh
. .venv/bin/activate
```

Activate on Windows PowerShell instead:

```powershell
.\.venv\Scripts\Activate.ps1
```

All remaining `python` commands assume this environment is activated and your working directory is the repository root. For local paths containing spaces, quote the entire argument.

### CPU installation (Linux/Windows wheels)

```sh
python -m pip install --upgrade pip
python -m pip install torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements-vision.txt
```

For macOS use the supported PyTorch/macOS installation rather than the Linux CPU wheel index. For NVIDIA GPU training, install the matching torch/torchvision CUDA builds using the [official PyTorch selector](https://pytorch.org/get-started/locally/), then install `requirements-vision.txt`. Keep torch/torchvision compatible; do not guess the CUDA version from the model name.

Check the installed environment:

```sh
python -c "import torch, torchvision, ultralytics; print('torch:', torch.__version__); print('torchvision:', torchvision.__version__); print('ultralytics:', ultralytics.__version__); print('CUDA:', torch.cuda.is_available())"
python -m unittest discover -s tests -v
```

The core simulator still needs only the standard library. Tests requiring Pillow/PyYAML are skipped when those optional dependencies are absent; check skip counts before claiming image validation was tested. Training requires the optional stack above.

If OpenCV import on Linux reports missing `libGL.so.1`, install the OS runtime libraries appropriate to your distribution; on Ubuntu a typical prerequisite is `sudo apt-get install libgl1 libglib2.0-0`. Do not disable TLS or package verification to resolve installation errors.

## 2. Place the annotated dataset on your machine

Export **YOLO detection boxes**, not segmentation polygons. For the example class map:

```text
0 = fastener_present
1 = fastener_missing
```

Freeze your reviewed class map before training. Missing fasteners require consistent boxes around expected fastener slots; see the annotation policy in the execution plan. If the slots are not resolvable, choose a larger visible target instead.

Use this layout, for example under `/absolute/path/to/aeris-data`:

```text
aeris-data/
  images/train/siteA_0001.jpg
  images/val/siteB_0001.jpg
  images/test/siteC_0001.jpg
  labels/train/siteA_0001.txt
  labels/val/siteB_0001.txt
  labels/test/siteC_0001.txt
  manifest.csv
```

A label file contains one box per line, normalized to image dimensions:

```text
0 0.50 0.40 0.08 0.06
1 0.72 0.40 0.08 0.06
```

The fields are `class_id center_x center_y width height`. Every image needs a label file. A reviewed negative image uses an empty file, not a missing file. Annotate all visible in-scope assets. Do not turn unreviewed images into negatives.

Create `manifest.csv` with one row per image, following [the template](../examples/image_detection/manifest.csv):

```csv
image,site,session,asset_group,split
images/train/siteA_0001.jpg,site-A,site-A-day-1,site-A-asset-1,train
images/val/siteB_0001.jpg,site-B,site-B-day-1,site-B-asset-1,val
images/test/siteC_0001.jpg,site-C,site-C-day-1,site-C-asset-1,test
```

Use actual metadata, not filenames guessed as site identities. Session and asset-group IDs must be globally unique (qualify them by site). Keep every view of a physical asset and session in the same split. The validator intentionally enforces site separation as well: you need independent sites for this evaluation workflow. If only one site exists, collect more data or design and document a different evaluation protocol; relabeling parts of one site as independent sites invalidates the experiment.

The validator accepts JPG/JPEG/PNG/BMP, nested image folders, and one image directory per split. Convert other formats explicitly and preserve source metadata. It does not support COCO JSON, polygon labels, lists of image paths, or remote dataset URLs directly.

## 3. Generate a machine-local YAML and validate annotations

Replace `/absolute/path/to/aeris-data` with your own dataset directory:

```sh
python -m aeris.vision configure --root /absolute/path/to/aeris-data --names fastener_present fastener_missing --output outputs/data-local.yaml
python -m aeris.vision validate --data outputs/data-local.yaml --manifest /absolute/path/to/aeris-data/manifest.csv
```

On Windows, for example, use `--root "D:/datasets/aeris-data"` and the corresponding manifest path. The configuration command writes an absolute dataset path. Recreate it when moving machines. If a configuration already exists, edit it deliberately or choose another output filename; commands refuse blind overwrites.

Expected output: image counts, boxes per class per split, dataset content hash, manifest hash, and YAML hash. Stop on missing labels, invalid boxes, unreadable images, orphan labels, missing manifest entries, cross-split duplicate content, or site/session/asset leakage. Every declared class needs training boxes.

This audit checks file consistency, not whether human annotations are correct or near-duplicate content has different encodings. Visually inspect exported box overlays and review a representative subset before continuing.

## 4. Run a short image-training smoke test

```sh
python -m aeris.vision train --data outputs/data-local.yaml --manifest /absolute/path/to/aeris-data/manifest.csv --model yolov8n.pt --epochs 1 --imgsz 640 --batch 2 --device cpu --output outputs/rail-smoke
```

The first use of `yolov8n.pt` can download general-purpose pretrained weights. These are initialization, not railway weights. Check the framework/weight license and retain provenance. The script validates data first, loads the model, runs training, and checks that the current run actually produced a `best.pt` file.

Expected files:

```text
outputs/rail-smoke/
  dataset-audit.json
  provenance.json
  training-result.json
  fit/
    args.yaml
    results.csv
    weights/best.pt
    weights/last.pt
```

Use the path printed in `training-result.json` as the authority. It also records the SHA-256 of `best.pt`. A completed one-epoch run only tests setup; inspect training samples and validation outputs for wrong labels or unusable resolution.

## 5. Train your actual railway detector to obtain best.pt

### CPU command

```sh
python -m aeris.vision train --data outputs/data-local.yaml --manifest /absolute/path/to/aeris-data/manifest.csv --model yolov8n.pt --epochs 100 --imgsz 1024 --batch 2 --device cpu --output outputs/rail-baseline
```

### NVIDIA GPU command (choose this instead when CUDA works)

```sh
python -m aeris.vision train --data outputs/data-local.yaml --manifest /absolute/path/to/aeris-data/manifest.csv --model yolov8n.pt --epochs 100 --imgsz 1024 --batch 4 --device 0 --output outputs/rail-baseline
```

Do not execute both commands with the same output directory. Each run directory must be new. `100` epochs and `1024` pixels are starting hyperparameters, not guaranteed best settings. First measure memory, throughput, and target feature size after resizing. Reduce batch size first for out-of-memory errors; reduce image size only after checking small-asset visibility. Windows defaults to `--workers 0`; the wrapper uses that cross-platform default everywhere.

The wrapper disables automatic mixed precision for a simpler reproducible starting run. Benchmark a separately versioned AMP configuration later if needed. It records seed, environment versions, dataset audit and training settings. Preserve full resolved dependencies too:

```sh
python -m pip freeze > outputs/rail-baseline/requirements-resolved.txt
```

Review output for credential-bearing custom package URLs before sharing it. Use this environment record plus OS/driver information to reproduce subsequent runs. Seeds alone do not guarantee identical GPU kernels.

**Your trained image detector is now:**

```text
outputs/rail-baseline/fit/weights/best.pt
```

`best.pt` is selected by the framework's validation fitness, not necessarily by your chosen recall/review budget. `last.pt` represents the latest saved state; final framework processing can strip optimizer state. Check the actual framework files rather than assuming every checkpoint can resume optimizer training.

If training was interrupted and `last.pt` retains training state, the pinned framework's direct resume pattern is:

```sh
python -c "from ultralytics import YOLO; YOLO('outputs/rail-baseline/fit/weights/last.pt').train(resume=True, device='cpu')"
```

This is an external-framework resume, not the wrapper's new-run path. It writes into the previous framework run. Verify the resumed epoch, optimizer state, dataset path and new weight hashes; refresh your provenance afterward. If state was stripped, start a new fine-tuning experiment with `--model path/to/checkpoint.pt` and a new output directory rather than claiming exact optimizer resumption.

## 6. Evaluate validation first, then the locked test split

```sh
python -m aeris.vision evaluate --data outputs/data-local.yaml --manifest /absolute/path/to/aeris-data/manifest.csv --weights outputs/rail-baseline/fit/weights/best.pt --split val --imgsz 1024 --device cpu --output outputs/rail-validation
```

Inspect `outputs/rail-validation/evaluation.json` and the framework plots under `metrics/`. Use validation data to select confidence thresholds, preprocessing, and model variants. Report per-class errors, small-object performance, bad-quality exclusions and review workload.

After freezing those choices:

```sh
python -m aeris.vision evaluate --data outputs/data-local.yaml --manifest /absolute/path/to/aeris-data/manifest.csv --weights outputs/rail-baseline/fit/weights/best.pt --split test --imgsz 1024 --device cpu --output outputs/rail-test
```

Replace `--device cpu` with `--device 0` for a configured GPU. The wrapper records AP/precision/recall from the framework and model/dataset hashes. It does not compute confidence intervals, route-level false alarms per kilometer, or automatic threshold selection. Those require a separate research evaluation with spatial grouping and independent confirmation.

An empty prediction is not evidence of a healthy observed asset. Separate visibility from defect classification. Keep the final test set out of threshold tuning.

## 7. Predict on new UAV photos and save evidence

Replace `/absolute/path/to/new-uav-images` with a local folder or one local image:

```sh
python -m aeris.vision predict --weights outputs/rail-baseline/fit/weights/best.pt --source /absolute/path/to/new-uav-images --conf 0.25 --imgsz 1024 --device cpu --output outputs/uav-predictions
```

`0.25` is an example only; replace it with the validation-selected threshold. This command reads still images (not a live UAV stream), loads the model once, and writes:

```text
outputs/uav-predictions/predictions.json
outputs/uav-predictions/000000-image-name.jpg
```

Each record includes original-image pixel boxes, class names/IDs, confidence, image hash/dimensions, and model hash. Annotated JPEGs support visual review. `quality_ok` and `anomaly_score` are null because this model does not determine either. Full detections remain in evidence records rather than being collapsed into one scalar.

Do not commit private images or `.pt` files to ordinary Git. Keep versioned model artifacts, manifests and evaluation reports in appropriate storage.

## 8. Connect image evidence to mission coverage

Prepare a review manifest:

```sh
python scripts/create_replay_manifest.py --predictions outputs/uav-predictions/predictions.json --output outputs/uav-replay.json
```

The generated rows begin **unaccepted**:

```json
[
  {"segment":0,"image":"/absolute/path/to/image.jpg","quality_ok":false,"asset_observed":false}
]
```

Open `outputs/uav-replay.json`. Put images in the real route order and set segment IDs to contiguous integers from zero. The generator's initial order is only sorted file order, not a geographic route. Review focus, exposure, blur, target resolution and asset visibility. Set each boolean to true only when justified. The replay adapter does not estimate quality or geolocation automatically. It currently accepts one image per segment; dense multi-image/asset coverage needs a later evidence association layer.

Replay into the abstract mission:

```sh
python -m aeris.vision replay --predictions outputs/uav-predictions/predictions.json --manifest outputs/uav-replay.json --alert-classes fastener_missing --output outputs/image-mission
```

`--alert-classes` names the classes that require human review; do not include a healthy class such as `fastener_present`. Choose them to match your actual model. Predictions already apply the inference threshold. A true `review_required` is a candidate, not confirmed damage.

Inspect `outputs/image-mission/mission.json` and `checkpoint.json`. Missing predictions or changed image contents are rejected. Unaccepted quality/visibility blocks verified coverage. A long route can be energy-infeasible under the simplified single-dock model; increasing sortie count cannot fix unreachable geometry.

For a deliberately interrupted run:

```sh
python -m aeris.vision replay --predictions outputs/uav-predictions/predictions.json --manifest outputs/uav-replay.json --alert-classes fastener_missing --max-sorties 1 --output outputs/image-partial
```

If incomplete, exit code 2 is expected. Resume with the same inputs:

```sh
python -m aeris.vision replay --predictions outputs/uav-predictions/predictions.json --manifest outputs/uav-replay.json --alert-classes fastener_missing --resume outputs/image-partial/checkpoint.json --output outputs/image-resumed
```

Keep `mission.json` beside the checkpoint. The replay command compares prediction/manifest hashes and alert classes to prevent silently changing evidence on resume. A completed checkpoint does not launch again. Resume preserves the verified boundary with overlap, not historical events or an airborne position. Dock checkpoints are not a transactional flight journal.

## 9. Export a local inspection report

```sh
python -m aeris.report --mission outputs/image-mission/mission.json --output outputs/image-mission/report.html
```

Open `report.html` as a local file in a browser. It contains the mission summary and escaped evidence records. This is a static export, not a hosted dashboard and not a reviewer database. Confirmation/rejection histories, image storage access controls, map transforms, asset deduplication and an audit database remain later implementation work.

## 10. Train unknown-anomaly detection using image embeddings

Do this after establishing the supervised model. YOLO class predictions alone are not open-set anomaly detection.

### 10.1 Prepare reviewed asset crops

Create consistently aligned asset/slot crops. Training and validation normals must be independently confirmed healthy. Include held-out-site normals and anomalies in test data; withhold complete anomaly categories for an unknown-category experiment. An encoder trained on anomaly examples from the final unknown categories invalidates that holdout, even if the normality fitting stage sees normals only.

Create `outputs/feature-images.jsonl` using [the template](../examples/image_detection/feature-images.jsonl), replacing all placeholder paths and metadata. Each line has:

```json
{"id":"site-A-slot-1","site":"site-A","day":"day-1","split":"train","segment":0,"label":"normal","quality_ok":true,"image":"/absolute/path/to/healthy-slot.jpg"}
```

For this numeric-feature workflow the split spelling is **`validation`**, whereas YOLO uses **`val`**. Include at least two accepted training normals, validation normals and both normal/anomaly accepted test records. Real research needs substantially more independent examples; these are only schema minimums.

### 10.2 Extract frozen image features

```sh
python -m aeris.vision features --weights outputs/rail-baseline/fit/weights/best.pt --manifest outputs/feature-images.jsonl --layer 9 --imgsz 224 --device cpu --output outputs/asset-features.jsonl
```

For pinned YOLOv8, layer 9 is the SPPF-stage feature block. The wrapper calls the framework's embedding interface and stores global-pooled vectors with encoder hash, image hash, layer and input size. It is a simple baseline, not PatchCore or a dense patch detector. Use the same encoder/layer/preprocessing for every split. The code checks layer bounds but does not certify semantic equivalence across different architectures; changing architecture requires a new experiment.

### 10.3 Fit and evaluate the normality model

```sh
python -m aeris.detection train --data outputs/asset-features.jsonl --model outputs/asset-normality.json --false-alarm-rate 0.05
python -m aeris.detection evaluate --data outputs/asset-features.jsonl --model outputs/asset-normality.json
```

`asset-normality.json` is a separate numeric anomaly model, not a replacement for `best.pt`. It fits per-dimension mean/scale on training normals and chooses an empirical threshold from validation normals. It is not a guaranteed 5% future false-alarm rate. Evaluate on independent sites and report unknown-category recall and reviewer burden.

Optional replay, if test segments have exactly one record each and are contiguous from zero:

```sh
python -m aeris.detection replay --data outputs/asset-features.jsonl --model outputs/asset-normality.json --output outputs/anomaly-mission
```

The supervised image replay and numeric anomaly replay are currently separate backends. A trained, calibrated multi-model fusion layer is not implemented. Do not compare unbounded anomaly distances directly with object confidence or present either as defect probability.

## 11. Verify mission continuity and abstract UAV control

These commands need no external autopilot:

```sh
python -m aeris --seed 27 --output outputs/sim-complete
python -m aeris --seed 27 --max-sorties 1 --output outputs/sim-partial
```

The second command intentionally exits 2 after the first sortie. Continue:

```sh
python -m aeris --resume outputs/sim-partial/checkpoint.json --output outputs/sim-resumed
python -m aeris.report --mission outputs/sim-resumed/mission.json --output outputs/sim-resumed/report.html
```

The tested example covers 40 segments over two sorties. `SimulatedUAV` has integer route position and abstract energy, not real pose or flight dynamics. `EnergySupervisor` checks next inspection + return + reserve + uncertainty. `CoverageLedger` prevents skipping a missing verified segment. The planner and world share the same cost equation, so these tests verify arithmetic, not real return-energy prediction.

The synthetic `aeris --resume` command cannot restore an image/anomaly backend. Use the dedicated image `replay --resume` command above for image experiments. Numeric-feature replay resumption still requires constructing the same `FeatureReplayDetector` and passing it to `Simulator.load(path, detector=detector)` in Python.

## 12. Install a separate PX4 SITL environment

**External setup; not executed or flight-validated in this change.** Use a local Linux machine with a desktop-capable simulator or a deliberately configured headless simulator. Keep the autopilot build outside this repository. A reproducible starting point is PX4 v1.15.0 on a supported Ubuntu environment, following its official release-specific prerequisites. Review the official compatibility requirements before running OS installers.

Example commands for a fresh local development machine:

```sh
mkdir -p ~/aeris-flight
cd ~/aeris-flight
git clone --branch v1.15.0 --recursive https://github.com/PX4/PX4-Autopilot.git
cd PX4-Autopilot
bash Tools/setup/ubuntu.sh
```

The setup script can require sudo, install OS packages, and request a reboot. Follow its output and the official PX4 documentation. This is not a portable Windows/macOS/cloud installation recipe. After required setup/reboot, in terminal A:

```sh
cd ~/aeris-flight/PX4-Autopilot
make px4_sitl gz_x500
```

Keep the simulator running. Confirm the vehicle and a valid home position. The build may be resource-intensive; choose parallelism for your machine rather than assuming all host CPUs are available. For an ArduPilot alternative, follow its official SITL workflow as a separate experiment; these scripts target the PX4/MAVSDK interface.

In terminal B, return to your AERIS checkout, activate its Python environment, and install the optional telemetry tools:

```sh
python -m pip install -r requirements-sitl.txt
python scripts/sitl_telemetry.py --timeout 30
```

The telemetry script listens on UDP 14540 and prints one position record. It never arms a vehicle. Timeout indicates no usable simulator telemetry; diagnose simulator launch, UDP routing and SDK compatibility before trying mission commands.

The pinned MAVSDK 3.17.4 package uses the inspected gRPC-style `mavsdk` API. It can emit a package-rename warning; do not silently upgrade to a native major version with a different API. The full PX4/MAVSDK pairing is not yet integration-tested here.

## 13. Execute the optional simulated waypoint demo

Use an **isolated simulated vehicle only** on UDP 14540. UDP by itself does not prove that a vehicle is simulated; do not route a physical autopilot into this port. The script is a vehicle-only development demo, without railway geometry, obstacle clearance, perception requests, or physical dock logic.

With terminal A still running PX4 SITL:

```sh
python scripts/px4_sitl_mission.py --execute --distance 10 --altitude 10 --timeout 180 --output outputs/sitl-demo-events.json
```

The supplied code waits for connection and global/home-position health, uploads three points (origin, approximately 10 m north, origin), requests return after mission completion, arms/starts the mission, and waits for landed/disarmed telemetry. It logs progress and requests return on failure when armed. A return request is not proof that return succeeded; inspect simulator behavior and logs after any failure.

Distances are restricted to a small nonpolar demo corridor. The coordinate conversion is a short-range approximation, not a survey/geodetic planning library. Timeouts and return requests do not replace the autopilot's configured failsafes. This script's API construction was checked against installed MAVSDK, but the mission itself was **not executed in SITL** in this cloud task.

Acceptance before integration: observed route execution, altitude and lateral error against simulator truth, successful return/landing, command/telemetry failure handling, and correctly enforced geofence. A zero exit without checking the resulting telemetry is insufficient for flight-validation claims.

## 14. Integrate camera, model and flight: next code milestone

There is no tested single command that combines the image backend with PX4 flight today. The synchronous `Simulator` cannot be used as a real-time flight controller by replacing one import. Implement this integration explicitly:

1. Add timestamped capture records with camera calibration, original image, pose, pose uncertainty, segment and asset IDs.
2. Add coordinate/clock transforms and tests using simulator ground truth. Document ENU/NED, degrees/radians, height reference, camera optical frame and clock offsets.
3. Implement an asynchronous mission supervisor with request IDs, acknowledgements, completion criteria, timeout and cancellation.
4. Run image inference in a worker and store full evidence before updating coverage. Reject stale/misaligned/poor-quality observations.
5. Define a bounded recapture policy. Every proposed camera/speed/route action must satisfy independent flight and energy constraints.
6. Inject missing frames, delayed inference, localization loss, command rejection and cloud outages in SITL.
7. Verify that inspection results never bypass autopilot failsafes or advance coverage without accepted evidence.

The working image replay is the test fixture for this future integration. Preserve its evidence contract rather than discarding boxes/model identity when moving to live streams. Configure the autopilot first; visual navigation, if added, is a separate segmentation/localization training problem, not YOLO defect confidence used as a steering signal.

## 15. Calibrate real energy, dock states and durable recovery

Current docking/charging are instantaneous simulated events. Physical landing guidance and charging verification are not implemented. Before adding them:

- Record voltage/current and elapsed time in consistent units, battery health, wind, speed, payload, ascent, temperature and actual return consumption.
- Fit a physical/regression baseline on training sessions; calibrate conservative residual margins on validation sessions; evaluate on held-out batteries/flights.
- Replace abstract costs only after testing underprediction, route reachability and available landing points. Maintain independent autopilot low-battery behavior.
- Implement explicit `RETURN`, `LANDING`, `DOCK_VERIFIED`, `CHARGING`, `MAINTENANCE`, and `READY` transitions with sensor-backed evidence and timeout behavior.
- Store an append-only evidence/event journal and transactional coverage state. Test interruption between capture, inference, evidence commit, landing and checkpoint writes.
- Resume only after verified charging/readiness and authorization; do not infer those states from process restart.

Use the current simulation/replay commands to test policy changes first. There is no physical dock command to run in this repository. Dock-specific interfaces and operational permissions depend on the selected hardware and site and must be implemented and validated separately.

## 16. Debugging and repeatability

| Symptom | Next action |
|---|---|
| Missing label / class mismatch | Fix the annotation export and class map; rerun `validate` |
| Site/session/asset leakage | Correct real split grouping; do not invent new site identities |
| No `best.pt` | Read the current run logs and `training-result.json`; do not reuse a stale file |
| GPU unavailable | Check the supported torch/driver installation; use the CPU command for setup checks |
| Out of memory | Lower batch size, then measure the effect of image-size changes |
| Model never detects a class | Review class counts, box overlays, slot visibility and camera resolution |
| Replay blocks on quality | Review real imagery and metadata; do not set acceptance true to force completion |
| Energy-infeasible route | Change the simulated energy/geometry assumptions explicitly; more retries are not a solution |
| Run directory already exists | Choose a new versioned output path; overwrite is intentionally refused |
| SITL timeout | Verify the simulator process, home/position health and UDP 14540 routing |

Keep `.pt`, raw imagery, `.venv`, and run artifacts outside ordinary Git. The repository ignores these common paths. Archive model hashes, dataset manifests, results, resolved dependency versions, OS/GPU details, and the source commit for every experiment. Do not claim field readiness from synthetic data, simulator-only checks or a high image mAP.

## 17. Reproduce the repository's image smoke test without railway data

This optional test trains on generated rectangles, from randomly initialized YOLO configuration weights, so it does not need pretrained model downloads. It verifies pipeline execution only. Use new output names if these already exist:

```sh
python scripts/create_vision_fixture.py --output outputs/geometry-data
python -m aeris.vision configure --root outputs/geometry-data --names rectangle_a rectangle_b --output outputs/geometry.yaml
python -m aeris.vision validate --data outputs/geometry.yaml --manifest outputs/geometry-data/manifest.csv
python -m aeris.vision train --data outputs/geometry.yaml --manifest outputs/geometry-data/manifest.csv --model yolov8n.yaml --epochs 1 --imgsz 64 --batch 2 --device cpu --output outputs/geometry-training
python -m aeris.vision evaluate --data outputs/geometry.yaml --manifest outputs/geometry-data/manifest.csv --weights outputs/geometry-training/fit/weights/best.pt --split test --imgsz 64 --device cpu --output outputs/geometry-evaluation
python -m aeris.vision predict --weights outputs/geometry-training/fit/weights/best.pt --source outputs/geometry-data/images/test --imgsz 64 --device cpu --output outputs/geometry-predictions
```

No good accuracy is expected from this one-epoch test. It is useful for diagnosing installation and dataset/training/inference flow before using your valuable labeled railway data.
