from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


def load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@dataclass(frozen=True)
class AmmeterCfg:
    name: str
    host: str
    port: int
    command: bytes


@dataclass(frozen=True)
class SamplingCfg:
    measurements_count: Optional[int]
    total_duration_seconds: Optional[float]
    sampling_frequency_hz: float


@dataclass(frozen=True)
class VisualizationCfg:
    enabled: bool
    plot_types: List[str]


@dataclass(frozen=True)
class AnalysisCfg:
    metrics: List[str]
    visualization: VisualizationCfg


@dataclass(frozen=True)
class ResultMgmtCfg:
    save_path: Path
    save_format: str  # 'json' or 'csv'
    metadata_fields: List[str]


@dataclass(frozen=True)
class DatadogCfg:
    enabled: bool = False
    host: str = "127.0.0.1"
    port: int = 8125
    namespace: str = "ammeter_test"


@dataclass(frozen=True)
class FaultInjectionCfg:
    enabled: bool = False
    drop_prob: float = 0.0
    delay_prob: float = 0.0
    delay_ms_min: int = 0
    delay_ms_max: int = 0
    corrupt_prob: float = 0.0
    outlier_prob: float = 0.0
    outlier_scale: float = 5.0


@dataclass(frozen=True)
class ProjectConfig:
    ammeters: List[AmmeterCfg]
    sampling: SamplingCfg
    analysis: AnalysisCfg
    results: ResultMgmtCfg
    datadog: DatadogCfg
    fault_injection: FaultInjectionCfg


def parse_config(raw: Dict[str, Any]) -> ProjectConfig:
    # Sampling
    sampling_raw = (raw.get("testing") or {}).get("sampling") or {}
    sampling = SamplingCfg(
        measurements_count=sampling_raw.get("measurements_count"),
        total_duration_seconds=sampling_raw.get("total_duration_seconds"),
        sampling_frequency_hz=float(sampling_raw.get("sampling_frequency_hz", 1.0)),
    )

    # Ammeters
    ammeters_raw = raw.get("ammeters") or {}
    ammeters: List[AmmeterCfg] = []
    for name in ("greenlee", "entes", "circutor"):
        if name not in ammeters_raw:
            continue
        a = ammeters_raw[name] or {}
        ammeters.append(
            AmmeterCfg(
                name=name,
                host=a.get("host", "localhost"),
                port=int(a["port"]),
                command=str(a["command"]).encode("utf-8"),
            )
        )

    # Analysis
    analysis_raw = raw.get("analysis") or {}
    viz_raw = (analysis_raw.get("visualization") or {})
    analysis = AnalysisCfg(
        metrics=list(analysis_raw.get("statistical_metrics") or []),
        visualization=VisualizationCfg(
            enabled=bool(viz_raw.get("enabled", False)),
            plot_types=list(viz_raw.get("plot_types") or []),
        ),
    )

    # Results
    rm_raw = raw.get("result_management") or {}
    results = ResultMgmtCfg(
        save_path=Path(rm_raw.get("save_path", "results/")),
        save_format=str(rm_raw.get("save_format", "json")).lower(),
        metadata_fields=list(rm_raw.get("metadata_fields") or []),
    )

    # Optional sections (not in the YAML by default, but required by your instructions)
    dd_raw = raw.get("datadog") or {}
    datadog = DatadogCfg(
        enabled=bool(dd_raw.get("enabled", False)),
        host=str(dd_raw.get("host", "127.0.0.1")),
        port=int(dd_raw.get("port", 8125)),
        namespace=str(dd_raw.get("namespace", "ammeter_test")),
    )

    fi_raw = raw.get("fault_injection") or {}
    fault_injection = FaultInjectionCfg(
        enabled=bool(fi_raw.get("enabled", False)),
        drop_prob=float(fi_raw.get("drop_prob", 0.0)),
        delay_prob=float(fi_raw.get("delay_prob", 0.0)),
        delay_ms_min=int(fi_raw.get("delay_ms_min", 0)),
        delay_ms_max=int(fi_raw.get("delay_ms_max", 0)),
        corrupt_prob=float(fi_raw.get("corrupt_prob", 0.0)),
        outlier_prob=float(fi_raw.get("outlier_prob", 0.0)),
        outlier_scale=float(fi_raw.get("outlier_scale", 5.0)),
    )

    return ProjectConfig(
        ammeters=ammeters,
        sampling=sampling,
        analysis=analysis,
        results=results,
        datadog=datadog,
        fault_injection=fault_injection,
    )
