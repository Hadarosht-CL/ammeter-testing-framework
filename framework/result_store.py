from __future__ import annotations

import csv
import json
import time
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List

from .config_loader import ProjectConfig
from .unified_api import Measurement


def new_run_id() -> str:
    ts = time.strftime("%Y%m%d_%H%M%S", time.localtime())
    return f"{ts}_{uuid.uuid4().hex[:8]}"


def measurement_to_dict(m: Measurement) -> Dict[str, Any]:
    return {
        "ammeter": m.ammeter,
        "timestamp_monotonic": m.timestamp_monotonic,
        "wall_time_epoch": m.wall_time_epoch,
        "value_a": m.value_a,
        "latency_s": m.latency_s,
        "ok": m.ok,
        "error": m.error,
    }


class ResultStore:
    def __init__(self, cfg: ProjectConfig):
        self.cfg = cfg
        self.base = cfg.results.save_path

    def create_run_dir(self) -> Path:
        run_id = new_run_id()
        run_dir = self.base / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir

    def write_config_snapshot(self, run_dir: Path, raw_yaml: Dict[str, Any]) -> None:
        (run_dir / "config.json").write_text(json.dumps(raw_yaml, indent=2), encoding="utf-8")

    def write_measurements(self, run_dir: Path, measurements: List[Measurement]) -> None:
        fmt = self.cfg.results.save_format
        rows = [measurement_to_dict(m) for m in measurements]
        if fmt == "csv":
            out = run_dir / "measurements.csv"
            with out.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else [])
                if rows:
                    writer.writeheader()
                    writer.writerows(rows)
        else:
            out = run_dir / "measurements.json"
            out.write_text(json.dumps(rows, indent=2), encoding="utf-8")

    def write_summary(self, run_dir: Path, summary: Dict[str, Any]) -> None:
        (run_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    def write_metadata(self, run_dir: Path, metadata: Dict[str, Any]) -> None:
        """Write metadata, filtered by config metadata_fields."""

        fields = set(self.cfg.results.metadata_fields or [])
        if not fields:
            # If not specified, keep everything provided.
            filtered = metadata
        else:
            filtered = {k: v for k, v in metadata.items() if k in fields}
        (run_dir / "metadata.json").write_text(json.dumps(filtered, indent=2), encoding="utf-8")
