# Making the airframe kit and flight controller yourself

This guide answers the second meaning of “make a UAV”: designing the frame, harness/power system and controller PCB rather than assembling an existing kit. It is an advanced engineering path. It does not turn a worksheet into a validated aircraft, and no fabrication-ready CAD/Gerber or custom flight firmware is supplied here.

For a school beginner, first complete the [supported-kit manual](student_build_manual.md) with an instructor. Use that working system as the measurement reference. A custom flight controller is a separate electronics project; do not make the first flight depend on first-revision PCB behavior.

## 1. Divide “make everything” into five projects

| Project | What you design | What you normally procure |
|---|---|---|
| Mechanical kit | Frame geometry, mounts, harness routing, assembly instructions | Rated motors, ESCs, propellers, fasteners and batteries |
| Power/harness | Rated wiring/distribution, regulators, connectors, measurement | Qualified converters/modules and documented connectors |
| Flight-controller PCB | Sensor/MCU/power/interface schematic, PCB and firmware target | Semiconductors, sensors, assembled PCB manufacturing |
| Companion/camera | Mounting, OS/runtime, capture and evidence integration | Supported computer module/carrier and camera/lens |
| System validation | Fixtures, procedures, fault tests and records | Test instruments and qualified review/operation |

Do not manufacture lithium cells, propellers or an RF radio system as incidental steps in a beginner AI project. Buying rated components does not prevent meaningful mechanical/electronics/software research.

## 2. Designing a custom airframe kit

### Step A — write measurable requirements

Specify payload mass and location, all-up mass target, required image geometry, controlled test conditions, endurance target, transport/maintenance needs and component support constraints. Begin with measured camera/companion mass and power. Choose motors/ESCs/propellers/battery as a documented compatible system rather than choosing each from maximum advertised numbers.

Deliverable: requirements sheet plus a mass/power table with part numbers and source curves. Do not claim endurance from nominal battery energy divided by an assumed hover load.

### Step B — mechanical CAD and load assessment

Use a mechanical CAD tool such as FreeCAD for plates/arms, mounting holes, landing gear, battery retention, camera and computer mounts. Define the controller body-axis orientation and camera view. Check center of gravity, propeller sweep, wiring/airflow access and fastener/tool clearance.

Use material data, load cases and qualified structural review to select arm/plate geometry and joints. A visualization or 3D print is not a strength test. Do not assume a printed polymer motor arm is adequate because it fits the motor. Carbon composites require appropriate machining/dust handling and electrical insulation provisions.

Deliverables: dimensioned drawings, assembly model, material/fastener specification, reviewed load cases and a prototype inspection procedure.

### Step C — make and inspect mechanical prototypes

Prototype non-flight mounts first. Verify hole alignment with the actual hardware, retention, camera line of sight, regulator cooling and service access. Test mounts with inert payloads where appropriate. Compare structural/vibration behavior against the reference kit. Retain revisions and test records; do not overwrite the CAD version that produced a failed part.

Deliverables: inspection records, measured mass/balance and revised drawings. The reference kit remains the flight platform until the custom assembly is independently evaluated.

### Step D — turn the design into a kit

Create a packing list and label each bag/part. Include screw length/grade, washers/spacers, specified assembly order, torque/thread treatment from the reviewed design, wire/harness IDs, connector drawings and inspection points. Use original photos and exploded views of the actual assembly, not images of a different revision.

Deliverables: reproducible assembly manual, labeled parts, supplier list and versioned drawings. A school user should not need to guess which screw or power cable to use.

## 3. Flight-controller PCB: define scope before drawing a schematic

A controller may contain a main MCU, inertial sensors, pressure sensing, clocking, boot/debug interfaces, logging storage, regulators/protection, sensor/telemetry/RC buses and actuator outputs. Redundant sensors and fault containment introduce additional requirements. A companion computer cannot simply substitute for this real-time hardware by connecting motors to GPIO.

Begin with an openly documented, supported reference design whose license permits your intended use. Verify the license before copying schematic/layout material. Identify a maintained PX4-compatible processor/board architecture and the actual software support it requires. Do not start a flight design from a microcontroller dev-board tutorial plus an unreviewed sensor breakout.

### Stage 1 — requirements and interface control

Record:

- Supported PX4 release/toolchain and whether an existing board target can legitimately be used or a new one is required.
- Required control/estimation/logging rates and timing budgets.
- Exact sensors and bus topology, interrupt lines, orientation and power requirements.
- Power sources, normal/fault voltages, current budgets and reset/brownout requirements.
- Serial, RC, CAN, USB and actuator interface electrical requirements.
- Boot/recovery/debug method and logging storage.
- Environmental, vibration, thermal, mass and mechanical constraints.

Deliverable: requirements document and connector/interface control table. Leave no pin labeled only “some UART.”

### Stage 2 — schematic in a tool such as KiCad

Create functional sheets for power entry/regulation/protection, MCU/clock/reset/boot/debug, each sensor, storage, USB, serial/RC/CAN and actuator outputs. Use component manufacturer reference circuits and exact datasheets. Verify symbol pin numbering against packages and actual procurement part numbers.

Assign explicit MCU alternate functions and check that sensor buses, DMA/interrupt needs, debugging, boot and outputs can coexist. Plan voltage domains and level translation. Add appropriate test points and board identity/revision markings. Follow the chosen reference design's validated approach to sensor filtering and power integrity; do not invent a universal capacitor/regulator recipe.

Deliverable: reviewed schematic, BOM, power tree, pin-assignment table and electrical-rule report. Passing ERC does not prove correctness.

### Stage 3 — PCB stack-up/layout review

Choose the layer stack-up with the manufacturer. Review return paths, decoupling, clock/USB/CAN requirements, noisy power/actuator coupling, sensor orientation/location, thermal behavior and mechanical clearances. Route and place according to component/interface guidance and qualified design review, not a generic screenshot.

Check footprints, connector keying, mounting holes, solder-mask/paste, assembly tolerances, test-point access and inspection visibility. Audit all external connectors for pin order and potential back-powering. Keep dangerous energy out of signal connectors by design.

Deliverable: reviewed PCB revision, design-rule results, fabrication/assembly drawings, BOM and pick-and-place outputs. These become manufacturing inputs only after review; this repository does not supply them.

### Stage 4 — manufacture a small prototype batch

Use a qualified PCB/assembly service and traceable components. Obtain inspection reports where available, preserve component substitutions for review and mark every board revision/serial number. A low-cost assembled board is not evidence of sensor or power correctness.

Deliverable: a small traceable prototype batch and assembly inspection records. Do not order a class set before first-board electrical tests.

### Stage 5 — electrical bring-up, no motors/propellers

Have a qualified electronics reviewer define the current-limited bench procedure and pass limits from the schematic. Inspect assembly/polarity/shorts before power. Verify each rail and startup/reset behavior, boot/debug access, clocking, MCU programming and temperatures. Bring up buses/sensors one subsystem at a time.

Confirm real sensor IDs, orientation, noise, timestamp/interrupt behavior and storage integrity. Exercise input/output interfaces using appropriate fixtures and loads, not aircraft propulsion. Test brownout/reset/recovery and approved USB/power combinations. A successful USB enumeration is only one small check.

Deliverable: measured rail/timing/sensor/interface results with failures and corrected revisions. Keep flight loads disconnected.

### Stage 6 — bootloader and PX4 board support

Implement or adapt a correctly licensed board target for the actual hardware. This can involve bootloader/flash layout, clocks, pin multiplexing, bus/driver configuration, sensor rotations, timer/actuator mappings, DMA resources, startup, storage, board identification and recovery behavior. A Pixhawk-like connector layout does not entitle a board to use a different board's firmware image.

Use the PX4 release's developer/porting documentation and build/test procedures. Review the real-time execution and estimator behavior under logging/telemetry loads. Maintain an independent recovery/programming path. Do not start by rewriting stabilization algorithms or copying motor-mixer coefficients from a different airframe.

Deliverable: version-controlled hardware target, reproducible build and flash/recovery instructions plus timing/resource results.

### Stage 7 — hardware/software validation

Test outputs and bus behavior with instrumentation. Compare sensor data and estimator behavior against a reference controller under controlled motion. Exercise watchdog/reset, storage-full, missing sensor, corrupted/stale input and communications failures using reviewed fixtures. Software- or hardware-in-the-loop testing can validate scenarios but does not replace electrical/environmental testing.

Deliverable: requirements-traced validation report. Unexplained resets, timing failures, incorrect orientation or lost-output conditions block integration. A blinking LED or a passed firmware build is not flight readiness.

### Stage 8 — controlled aircraft integration

Only after independent review should a custom controller be evaluated on a test aircraft under the applicable operating procedure. Repeat actuator mapping, estimation, power, telemetry and contingency qualification rather than transferring confidence from the reference kit. Use qualified operation and incremental tests. Keep all custom-board failures visible in the record.

## 4. Designing the power harness yourself

Prepare a power tree and current/temperature budget from exact devices, including startup/transient loads and converter losses. Select connector/wire/routing/protection based on rated conditions and qualified review. Design strain relief, polarity/keying, service isolation and sensor power references. Do not guess wire size from color or battery capacity alone.

Make controlled assembly drawings for every cable and a continuity/polarity test specification. Use proper crimp tools and documented connector terminals. High-current solder joints and lithium battery handling are instructor/qualified-builder work. Bench-test regulators/harnesses against the specified loads before attaching expensive computers or flight electronics.

## 5. What files a genuinely complete custom design must contain

```text
custom-design-revision-X/
  requirements-and-review-records/
  mechanical-cad-and-dimensioned-drawings/
  schematics-pcb-and-stackup/
  bom-and-approved-substitutions/
  fabrication-and-assembly-packages/
  harness-connector-and-pin-tables/
  firmware-board-target-and-build-record/
  bench-fixtures-and-pass-limits/
  electrical-sensor-timing-environmental-results/
  system-integration-and-failure-records/
  beginner-assembly-and-inspection-manual/
```

This list is the acceptance checklist for claiming “we made a UAV kit/controller,” not files that already exist here. To produce them, exact requirements and parts must first be selected and engineered. The supported-kit manual and worksheets provide a practical starting project without falsely claiming a flight-ready custom PCB.

## 6. References

- KiCad schematic/PCB/manufacturing documentation: https://docs.kicad.org/
- FreeCAD documentation: https://www.freecad.org/ and https://www.freecad.org/documentation.php
- PX4 hardware and porting developer documentation: https://docs.px4.io/main/en/hardware/ and https://docs.px4.io/main/en/development/development.html
- Pixhawk hardware standards/reference ecosystem: https://pixhawk.org/
- Exact controller/kit manuals: https://docs.holybro.com/

Review licenses, revision-specific datasheets and the current official release documentation before copying designs or ordering hardware. No custom circuit, manufactured kit or flight test was performed for this guide.
