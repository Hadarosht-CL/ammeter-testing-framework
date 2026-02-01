from __future__ import annotations

import argparse
from pathlib import Path

from framework.config_loader import load_yaml, parse_config
from framework.runner import run_project


def main() -> int:
    ap = argparse.ArgumentParser(description="Run ammeter testing framework")
    ap.add_argument(
        "--config",
        default=str(Path("config") / "test_config.yaml"),
        help="Path to YAML config (default: config/test_config.yaml)",
    )
    args = ap.parse_args()

    cfg_path = Path(args.config)
    raw = load_yaml(cfg_path)
    cfg = parse_config(raw)

    run_dir = run_project(cfg, raw)
    print(f"\nRun complete. Results written to: {run_dir}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
