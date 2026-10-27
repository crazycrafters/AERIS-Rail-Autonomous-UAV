# AERIS-Rail

Research software for railway UAV inspection mission continuity. **Simulation only:** no aircraft commands, flight interface, real detector, or field safety claims.

Requires Python 3.10+; no external dependencies.

```sh
python -m unittest discover -s tests -v
python -m aeris --seed 27 --output outputs/demo
python -m aeris --resume outputs/demo/checkpoint.json --output outputs/resumed
```

The CLI writes `mission.json` (events and synthetic observations) and an atomically replaced `checkpoint.json`. Exit 0 means complete coverage; exit 2 means an explicitly reported blockage or sortie limit. Resume restores configuration and verified coverage, starts at the dock with a full battery, and reinspects one segment of overlap. Historical events remain in the preceding mission output; they are not merged into resumed output. Checkpoints are saved after docking, not during flight. A real system would require an append-only journal and crash recovery.

Seed 27 demonstrates completion; default seed 7 deliberately permits deterministic poor-quality images and can block progress. Quality rejection is never silently counted as coverage. Scores and labels are synthetic and cannot measure perception accuracy.

See [doctoral research essay](docs/doctoral_research_essay.md) for the research questions, mathematical formulation, experimental design, and implementation boundaries. The single dock and constant wind model can make distant segments unreachable; increasing sortie count cannot solve that geometry. Charging and docking are discrete simulated events, without physical dynamics or elapsed charging time.
