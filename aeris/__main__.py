import argparse
import json
from pathlib import Path
from .simulation import Config, Simulator


def main():
    p = argparse.ArgumentParser(description="Simulation only; no aircraft control")
    p.add_argument("--output", type=Path, default=Path("outputs"))
    p.add_argument("--resume", type=Path)
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--segments", type=int, default=40)
    p.add_argument("--max-sorties", type=int, default=100)
    a = p.parse_args()
    if a.max_sorties < 1:
        p.error("--max-sorties must be positive")
    sim = Simulator.load(a.resume) if a.resume else Simulator(Config(seed=a.seed, segments=a.segments))
    a.output.mkdir(parents=True, exist_ok=True)
    result = sim.run(a.output / "checkpoint.json", a.max_sorties)
    (a.output / "mission.json").write_text(json.dumps(result, indent=2))
    print(json.dumps({k: v for k, v in result.items() if k not in ("events", "observations")}))
    return 0 if result["status"] == "completed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
