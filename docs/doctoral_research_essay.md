# AERIS-Rail: Evidence-Constrained Autonomous Railway Inspection Across Energy-Limited UAV Sorties

**Doctoral research proposal and executable mission-level prototype**  
**Status:** proposed methods; no empirical field-performance claims.

## Abstract

Autonomous railway inspection is a coupled problem of navigation, visual observability, decision uncertainty, energy feasibility, and durable evidence management. A vehicle can traverse a corridor without acquiring useful inspection evidence, and a perception model can produce confident predictions without establishing either defect validity or flight safety. This proposal develops AERIS-Rail as a constrained inspection architecture in which verified coverage, rather than distance flown, is the principal mission outcome. A hierarchical supervisor separates vehicle safety from inspection objectives, while complementary supervised recognition and open-set anomaly scoring support evidence-based human triage. Energy-to-dock estimates constrain each proposed inspection action, and persistent coverage records support continuation across sorties. Five falsifiable hypotheses address navigation fusion, unknown-anomaly retrieval, reserve preservation, checkpointed continuation, and temporal registration. The accompanying standard-library Python implementation exercises a deliberately restricted mission model: one-dimensional movement, synthetic observations, deterministic energy consumption, simulated docking, and checkpoint restoration. It establishes executable software behavior, not visual diagnostic validity or operational autonomy. A staged evaluation protocol specifies the additional datasets, baselines, uncertainty analyses, and simulator integrations needed to support doctoral contributions.

## 1. Problem definition and scientific motivation

Railway infrastructure is geographically distributed, visually heterogeneous, and operationally constrained. UAV imagery can supplement inspection of exposed assets, including sleepers, fasteners, ballast, vegetation, and obstructions. Its utility depends on resolution, illumination, geometry, motion blur, and asset visibility. Neither aerial RGB imagery nor an anomaly score can exclude internal rail defects. The intended system therefore produces observations and review candidates within a defined sensing envelope; it does not certify infrastructure safety.

The scientific problem is to allocate limited flight energy to geographically complete and diagnostically useful inspection while preserving independent safety constraints. Treating this as object detection alone discards the reasons a camera observation may be absent, misleading, spatially misassigned, or operationally unrecoverable. Conversely, treating it as waypoint following conflates traversal with inspection success. AERIS-Rail makes that distinction explicit through a verified coverage ledger.

A segment is verified only if the required asset regions are observed at adequate quality and associated with a sufficiently reliable location. Verification here concerns acquisition completeness, not proof that the asset is healthy. This distinction must remain visible in both software schemas and operator interfaces.

## 2. Research gap and proposed contribution

Railway following, visual defect recognition, novelty detection, return-to-home control, and automated docking are established areas. Their combination is not itself sufficient evidence of novelty. The proposed doctoral contribution is a formally specified and experimentally evaluated coupling between observation validity, mission continuation, and conservative return decisions.

Three artifacts would support that contribution: an evidence-aware mission state machine; a benchmark linking acquisition failures and energy constraints to completed inspection coverage; and a reproducible evaluation of complementary known/unknown perception under geographic distribution shift. Novelty remains conditional on a systematic literature review and comparisons against strong contemporary methods.

The references in the source essay are leads, not independently verified findings in this repository. In particular, publication metadata, maturity claims, and reported results must be checked against primary sources before submission. This proposal does not infer performance from those leads.

## 3. Research questions and falsifiable hypotheses

**RQ1: When does visual rail evidence improve corridor navigation?** H1 predicts that route-constrained fusion reduces cross-track error and branch-selection errors relative to waypoint-only and vision-only baselines under controlled localization degradation. Improvement must not be obtained by increasing unsafe continuation under track ambiguity.

**RQ2: Can unknown conditions be retrieved without overwhelming reviewers?** H2 predicts that complementary supervised and normality-based scores improve held-out anomaly recall at a predeclared false-alarm budget compared with either path alone. A threshold selected after inspecting test outcomes would invalidate this comparison.

**RQ3: Does predictive return planning improve energy feasibility?** H3 predicts fewer reserve violations than fixed state-of-charge thresholds under matched route, battery, and wind realizations. A trivial policy that always aborts is excluded by also reporting completed verified coverage and launch count.

**RQ4: Does persistent coverage improve interrupted missions?** H4 predicts greater unique verified distance under a fixed energy and sortie budget than stateless restart, with comparable observation quality. Checkpoint corruption and stale records must be included as failure cases.

**RQ5: Does temporal alignment reduce nuisance alerts?** H5 predicts fewer non-actionable alerts after asset-aligned historical comparison at matched true-anomaly recall. Registration uncertainty must be measured rather than assumed negligible.

## 4. System architecture and trust boundaries

The vehicle layer comprises an autopilot, localization sensors, obstacle sensing, and vehicle-level failsafes. A mission supervisor requests inspection actions only within a permitted operating envelope. The inspection layer estimates asset regions, observation quality, known-defect confidence, and visual novelty. Ground infrastructure manages docking, charging status, maintenance readiness, and authorization. A later dashboard stores geographically indexed evidence and review decisions.

Inspection confidence must never substitute for obstacle clearance or vehicle localization confidence. Cloud connectivity must not be a prerequisite for local contingency execution. A deployment would require explicit behavior for lost localization, corridor disagreement, communications loss, degraded battery health, failed docking, unavailable charging, and unavailable alternate landing locations.

This repository implements none of those vehicle interfaces. Its supervisor is a mission-level arithmetic constraint inside a simulator, not a certified flight-safety controller. Docking and charging are state transitions without physical guidance, electrical modeling, or environmental checks.

## 5. Formal model

Let the corridor comprise ordered segments i = 1,...,N. Let x_t denote vehicle and mission state, b_t usable energy, and z_i the evidence state of segment i. In a physical system these quantities are uncertain; a belief distribution over localization, energy, and observation validity is more appropriate than perfect state knowledge.

Define verified coverage as C = sum_i L_i v_i, where L_i is segment length and v_i indicates satisfaction of a predeclared acquisition criterion. An illustrative objective is to maximize E[C + alpha A - beta F - gamma E_used], where A measures confirmed actionable information and F review burden. These terms have incompatible units until weights and normalization are specified. They must be justified through sensitivity analysis, not selected to favor a proposed method.

For a candidate action a, impose:

    b_t >= E_action(a) + E_return(x_after_action, dock) + E_reserve + M_uncertainty

The reserve is not an objective penalty that can be traded away. In a stochastic extension, impose a chance constraint P(E_action + E_return <= b_t - E_reserve) >= 1 - delta. Selecting delta requires an operational risk argument and calibrated uncertainty estimates. A constant margin does not establish a probabilistic guarantee.

A single dock also imposes a reachability boundary. Splitting a long route into more sorties cannot make every distant segment reachable. Dock placement, alternate landing sites, payload, and battery capacity become planning variables in a subsequent model.

The implementation uses a constant per-distance travel cost multiplied by a fixed wind factor and a constant per-segment inspection cost. Outbound and inbound costs are symmetric. Its return estimate exactly matches its own simulated consumption, so reserve preservation tests arithmetic consistency under model assumptions; they do not validate energy prediction under uncertainty.

## 6. Inspection and unknown-anomaly inference

A future perception pipeline should first localize relevant assets and assess observability. Supervised models recognize predefined conditions; a normality model estimates departure from verified healthy examples. PatchCore, PaDiM, and teacher-student approaches are candidate families, not selected implementations. Comparing methods requires consistent backbones, resolution budgets, training splits, and inference hardware.

Unknown anomalies should be held out by semantic category as well as site. Score fusion should be calibrated on validation data, with explicit handling of disagreement. A maximum of scores is easy to implement but is not generally a calibrated probability. Repeated observations can strengthen evidence only when their dependence and registration quality are considered.

The current code generates synthetic scores and quality flags from a per-segment random seed. A review flag follows thresholding of the maximum score when quality passes. This is an interface placeholder that exercises evidence flow, not a trained detector, an open-set benchmark, or a demonstration of H2. Synthetic truth is exposed solely for transparent simulation inspection and must never become a model input in real experiments.

## 7. Coverage persistence and recovery semantics

A durable record should distinguish requested traversal, captured images, accepted acquisition, pending review, and confirmed findings. Coverage must reference evidence identifiers, sensor calibration, position uncertainty, timestamps, and acceptance rules. A crash between image acquisition and ledger commit requires idempotent recovery, not unconditional advancement.

The prototype persists configuration and the contiguous verified segment boundary after docking. An atomic temporary-file replacement reduces the risk of a partially written JSON checkpoint. It is not a transactional database, concurrent-writer protocol, or power-loss durability guarantee. Resume starts a new sortie at the dock, assumes a full battery, and reinspects one segment of overlap. Historical observations remain in the earlier output file.

A rejected image prevents progression and remains unresolved because the deterministic observation model repeats the same quality outcome. The simulator reports this blockage instead of inventing successful recapture. Adaptive camera actions, changing illumination, and retry budgets are future extensions. An interrupted process before docking restarts from the last docked checkpoint, potentially repeating acquisition. This limitation defines the implemented recovery contract.

## 8. Experimental methodology

The evaluation should proceed through three evidence tiers. Tier A validates mission software with deterministic scenarios and property-oriented checks. Tier B evaluates offline perception on licensed, annotated imagery with site/day separation. Tier C integrates vehicle and camera simulation to test navigation, latency, contingencies, and energy-model error. Physical trials are a separate, supervised stage and cannot be justified by success in the earlier tiers alone.

For H1, vary occlusion, parallel tracks, switches, localization noise, and route-map errors. Report cross-track error distributions, wrong-branch selections, track-loss detection latency, interventions, and completed coverage. Include simulator fidelity limits.

For H2 and H5, hold out collection sites and unknown defect categories. Report precision-recall curves, AUPRC, false alarms per kilometer, recall at a fixed review budget, calibration, and feature-size sensitivity. Include normal but unusual appearances such as wet rails and shadows. Historical comparisons must not leak future test imagery into training or threshold selection.

For H3, compare predictive and fixed-threshold policies on paired scenarios with common exogenous wind and battery realizations. Report reserve violations, prediction error, completed coverage, and abort rate. Perturb model parameters and introduce biased return estimates. Test infeasible routes explicitly.

For H4, inject interruptions at acquisition, checkpoint write, docking, and restart. Compare unique verified distance, duplicate captures, lost evidence, completion time, and recovery correctness against stateless restart. Count launches and all energy consumption; an extra sortie is not free.

Choose sample sizes from a power analysis using pilot variability and a minimum meaningful effect. Report confidence intervals using independent sites or mission realizations as sampling units, rather than treating correlated frames as independent. Predeclare primary outcomes, thresholds, exclusions, and multiplicity handling. Publish configurations, random seeds, dataset manifests, and raw mission traces where licensing permits.

## 9. Implementation scope and executable validation

The `aeris` package implements corridor movement, action-level energy checks, synthetic inspection observations, quality-gated coverage, return events, charging transitions, and JSON checkpoint restoration. The command-line interface exports mission traces and returns a nonzero status when the requested coverage is incomplete. Its standard-library-only design makes the first prototype reproducible without external services or credentials.

The accompanying unit tests exercise multi-sortie completion, reserve preservation at docking, interrupted-run recovery with overlap, insufficient-energy rejection, quality blockage, invalid parameters, and completed-checkpoint behavior. These tests support software-level claims within the simplified model. They do not establish any of the five scientific hypotheses, and no numerical perception, navigation, or field results are claimed here.

The next implementation milestone should replace synthetic observations with an offline image adapter and explicit evidence identifiers, before adding real-time flight integration. An experiment runner should then implement the named baselines and export aggregate metrics. ROS 2 and PX4 or ArduPilot software-in-the-loop can follow once message contracts, contingency states, and scenario acceptance criteria are defined.

## 10. Threats to validity and responsible interpretation

Internal validity is threatened by shared assumptions between the return planner and simulated world, synthetic labels constructed from the same generator as scores, and deterministic observability. External validity is limited by absent aerodynamics, train movements, catenary geometry, weather dynamics, and communication effects. Construct validity depends on whether acquisition criteria predict diagnostic usefulness, and whether reviewer-confirmed findings represent ground truth.

Operational inspection also depends on railway access, aviation authorization, competent oversight, security, maintenance, and data governance. Those are deployment prerequisites rather than outputs of a model score. Images may capture people or sensitive infrastructure; retention and access controls belong in the eventual data architecture. Cost-effectiveness requires measured review workload, downtime, maintenance, and missed-condition consequences. No return-on-investment claim is supportable from this prototype.

## 11. Conclusion

AERIS-Rail is best framed as evidence-constrained inspection continuity under uncertain perception and finite energy. Its prospective scientific value lies in demonstrating that the coupling improves measurable mission outcomes against credible alternatives. The initial software provides a transparent mission-level foundation and explicitly exposes quality and reachability failures. Advancing from that foundation requires licensed imagery, calibrated uncertainty, comparative experiments, and higher-fidelity simulation rather than stronger autonomy claims.

## Reference starting points

These sources identify established method families and official interfaces; they are not a completed systematic review. Web sources and bibliographic details require verification before academic submission.

1. Federal Railroad Administration. *Automated Track Centerline Following for Drone Flight Automation*, RR 22-15. https://railroads.dot.gov/elibrary/automated-track-centerline-following-drone-flight-automation
2. Roth et al. *Towards Total Recall in Industrial Anomaly Detection*. CVPR, 2022 (PatchCore).
3. Defard et al. *PaDiM: A Patch Distribution Modeling Framework for Anomaly Detection and Localization*. ICPR Workshops, 2021.
4. PX4. *Return Mode*. https://docs.px4.io/main/en/flight_modes/return.html
5. ArduPilot. *Battery Failsafe*. https://ardupilot.org/copter/docs/failsafe-battery.html

The uploaded AERIS-Rail essay supplied the initial architecture and hypotheses. This document reformulates those ideas as a research proposal and specifies the narrower implemented behavior. Its statements of intended methodology are not empirical findings.
