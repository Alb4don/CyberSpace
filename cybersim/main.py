import argparse
import json
import sys
from pathlib import Path
from .models import Config
from .engine import Engine

def data_path():
    import os
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share")))
    return base / "cyberspace-sim" / "episodes.sqlite3"

def main():
    parser = argparse.ArgumentParser(description="Autonomous cyberspace simulator")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--scenario", type=Path)
    parser.add_argument("--steps", type=int, default=24)
    parser.add_argument("--agents", type=int, default=3)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()
    try:
        config = Config(steps=args.steps, agents=args.agents, seed=args.seed)
        if args.headless:
            _, findings, metrics, episode = Engine(config, data_path(), args.scenario).run()
            print(json.dumps({"episode": episode, "paths": [f.model_dump() for f in findings],
                              "metrics": [m.model_dump() for m in metrics]}, indent=2))
        else:
            from .gui import launch
            raise SystemExit(launch(data_path()))
    except Exception:
        print("Simulation failed. Verify the local configuration and dependencies.", file=sys.stderr)
        raise SystemExit(1)

if __name__ == "__main__":
    main()
