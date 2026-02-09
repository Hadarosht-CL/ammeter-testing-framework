#!/usr/bin/env python3
"""
Config-driven end-to-end test runner.

Usage:
  python tests/run_config_e2e.py
  python tests/run_config_e2e.py --config configs/scenario_fault_injection.yaml

What it does:
  - Loads YAML config (default configs/sample_quick.yaml)
  - Validates required schema fields
  - Starts 3 ammeter emulators in background threads (same process)
  - Runs the framework entrypoint: python run_framework.py --config <tmp_cfg>
  - Verifies artifacts + summary includes required stats keys

This is an integration (E2E) test by design.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Dict, List

import yaml
from Utiles.Utils import load_yaml, override_results_path, validate_config_schema


DEFAULT_CFG = Path("configs/sample_quick.yaml")

# -------------------------
# Emulator bootstrap
# -------------------------

def _try_start_emulator_from_module(mod_name: str, port: int) -> threading.Thread:
    """
    Best-effort start of emulator servers using the existing Ammeters modules.
    We avoid hardcoding a single entrypoint function name by trying common patterns.

    Expected module names:
      Ammeters.Greenlee_Ammeter
      Ammeters.Entes_Ammeter
      Ammeters.Circutor_Ammeter
    """
    import importlib
    import inspect

    mod = importlib.import_module(mod_name)

    # 1) Common: module exposes run_server(port=...) / start_server(port=...)
    for fn_name in ("run_server", "start_server", "serve", "main"):
        fn = getattr(mod, fn_name, None)
        if callable(fn):
            sig = inspect.signature(fn)
            kwargs = {}
            if "port" in sig.parameters:
                kwargs["port"] = port
            # Some implementations accept host too, but config often assumes localhost.
            if "host" in sig.parameters:
                kwargs["host"] = "127.0.0.1"

            def _runner():
                fn(**kwargs)

            t = threading.Thread(target=_runner, daemon=True, name=f"{mod_name}:{port}")
            t.start()
            return t

    # 2) Common: module defines a class you instantiate and call .start() / .serve_forever() / .run()
    # Find a plausible class
    candidates = []
    for name, obj in vars(mod).items():
        if inspect.isclass(obj) and obj.__module__ == mod.__name__:
            if "ammeter" in name.lower() or "emulator" in name.lower() or "server" in name.lower():
                candidates.append(obj)

    if not candidates:
        raise RuntimeError(f"Could not find start function/class in {mod_name}")

    cls = candidates[0]
    sig = inspect.signature(cls)

    kwargs = {}
    if "port" in sig.parameters:
        kwargs["port"] = port
    if "host" in sig.parameters:
        kwargs["host"] = "127.0.0.1"

    inst = cls(**kwargs)

    # pick a method
    for meth_name in ("start", "serve_forever", "run", "start_server"):
        meth = getattr(inst, meth_name, None)
        if callable(meth):
            t = threading.Thread(target=meth, daemon=True, name=f"{mod_name}:{port}")
            t.start()
            return t

    raise RuntimeError(f"Found emulator class in {mod_name}, but no runnable method (start/run/serve_forever).")


def start_emulators_from_config(cfg: Dict[str, Any]) -> List[threading.Thread]:
    """
    Start exactly the three expected emulator types for the assignment.
    Uses the ports provided in the YAML.
    """
    am = cfg["ammeters"]

    # keys in YAML are expected to be like: greenlee / entes / circutor
    # We'll tolerate case variants.
    def _find_key(name: str) -> str:
        for k in am.keys():
            if k.lower() == name:
                return k
        raise ValueError(f"Missing ammeters.{name} in config")

    greenlee_key = _find_key("greenlee")
    entes_key = _find_key("entes")
    circutor_key = _find_key("circutor")

    threads = []
    threads.append(_try_start_emulator_from_module("Ammeters.Greenlee_Ammeter", int(am[greenlee_key]["port"])))
    threads.append(_try_start_emulator_from_module("Ammeters.Entes_Ammeter", int(am[entes_key]["port"])))
    threads.append(_try_start_emulator_from_module("Ammeters.Circutor_Ammeter", int(am[circutor_key]["port"])))

    # Give servers a moment to bind sockets
    time.sleep(0.3)
    return threads


# -------------------------
# Framework run + verify
# -------------------------

def run_framework(cfg_path: Path, timeout_s: int = 30) -> None:
    """
    Run the existing entrypoint script using subprocess
    (this ensures we're testing what the reviewer will run).
    """
    cmd = [sys.executable, "run_framework.py", "--config", str(cfg_path)]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s)
    if proc.returncode != 0:
        raise RuntimeError(
            "Framework run failed.\n"
            f"CMD: {' '.join(cmd)}\n"
            f"STDOUT:\n{proc.stdout}\n"
            f"STDERR:\n{proc.stderr}\n"
        )


def find_latest_run_dir(results_dir: Path) -> Path:
    """
    result_store creates a unique folder per run under save_path.
    We'll pick the newest directory.
    """
    dirs = [p for p in results_dir.iterdir() if p.is_dir()]
    if not dirs:
        raise AssertionError(f"No run folders found under results path: {results_dir}")
    return max(dirs, key=lambda p: p.stat().st_mtime)


def assert_artifacts_ok(run_dir: Path) -> None:
    summary_path = run_dir / "summary.json"
    if not summary_path.exists():
        raise AssertionError(f"Missing summary.json in {run_dir}")

    # measurements could be csv or json based on config
    meas_csv = run_dir / "measurements.csv"
    meas_json = run_dir / "measurements.json"
    if not (meas_csv.exists() or meas_json.exists()):
        raise AssertionError(f"Missing measurements.csv or measurements.json in {run_dir}")

    with summary_path.open("r", encoding="utf-8") as f:
        summary = json.load(f)

    # Verify per-meter stats contain required metrics
    # Expected structure per your README:
    # summary["per_meter"][meter]["stats"] includes mean/median/std/min/max (naming may vary)
    per_meter = summary.get("per_meter")
    if not isinstance(per_meter, dict) or not per_meter:
        raise AssertionError("summary.json missing per_meter stats")

    required = {"mean", "median", "std", "min", "max"}

    for meter_name, meter_obj in per_meter.items():
        stats = meter_obj.get("stats") if isinstance(meter_obj, dict) else None
        if not isinstance(stats, dict):
            raise AssertionError(f"{meter_name}: missing stats dict in summary")

        # allow "standard_deviation" naming etc, but require at least the canonical keys
        keys = {k.lower() for k in stats.keys()}
        missing = [k for k in required if k not in keys]
        if missing:
            raise AssertionError(f"{meter_name}: stats missing keys: {missing}. Found: {sorted(keys)}")

        # ensure there was data
        count = meter_obj.get("count", 0)
        if int(count) <= 0:
            raise AssertionError(f"{meter_name}: count <= 0 (no measurements recorded)")


# -------------------------
# Main
# -------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Config-driven E2E runner for ammeter project")
    parser.add_argument("--config", default=None, help="Path to YAML config. Default: configs/sample_quick.yaml")
    args = parser.parse_args()

    cfg_path = Path(args.config) if args.config else DEFAULT_CFG
    if not cfg_path.exists():
        print(f"ERROR: config file not found: {cfg_path}", file=sys.stderr)
        return 2

    cfg = load_yaml(cfg_path)
    validate_config_schema(cfg)

    # Use a temp results folder and rewrite config so verification is deterministic/clean
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        results_dir = tmpdir / "results"
        results_dir.mkdir(parents=True, exist_ok=True)

        cfg2 = override_results_path(cfg, results_dir)
        tmp_cfg_path = tmpdir / "effective_config.yaml"
        tmp_cfg_path.write_text(yaml.safe_dump(cfg2, sort_keys=False), encoding="utf-8")

        # Start emulators (threads)
        _threads = start_emulators_from_config(cfg2)

        # Run the actual framework script
        run_framework(tmp_cfg_path)

        # Verify artifacts
        run_dir = find_latest_run_dir(results_dir)
        assert_artifacts_ok(run_dir)

        print(f"PASS: E2E run succeeded. Artifacts at: {run_dir}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
