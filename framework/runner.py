from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, List

from .analysis import pairwise_agreement, reliability_ranking, stats_by_ammeter
from .config_loader import ProjectConfig
from .datadog_metrics import maybe_create_client
from .faults import FaultInjector
from .result_store import ResultStore
from .sampler import Sampler
from .unified_api import AmmeterClient, Measurement
from .visualization import render_plots


def run_project(cfg: ProjectConfig, raw_yaml: Dict[str, Any]) -> Path:
    clients = [AmmeterClient(a.name, a.host, a.port, a.command) for a in cfg.ammeters]
    dd = maybe_create_client(cfg.datadog)
    faults = FaultInjector(cfg.fault_injection)

    sampler = Sampler(clients=clients, sampling=cfg.sampling, fault_injector=faults, dd=dd)
    measurements: List[Measurement] = sampler.run()

    # Analysis
    stats = stats_by_ammeter(measurements)
    agreements = pairwise_agreement(measurements)
    ranking = reliability_ranking(stats, agreements)

    summary = {
        "generated_at_epoch": time.time(),
        "sampling": {
            "measurements_count": cfg.sampling.measurements_count,
            "total_duration_seconds": cfg.sampling.total_duration_seconds,
            "sampling_frequency_hz": cfg.sampling.sampling_frequency_hz,
        },
        "stats_by_ammeter": {k: s.__dict__ for k, s in stats.items()},
        "pairwise_agreement": {
            f"{a}__{b}": ag.__dict__ for (a, b), ag in agreements.items()
        },
        "reliability_ranking": ranking,
    }

    # Results
    store = ResultStore(cfg)
    run_dir = store.create_run_dir()
    store.write_config_snapshot(run_dir, raw_yaml)
    store.write_measurements(run_dir, measurements)
    store.write_summary(run_dir, summary)
    # A small set of metadata fields are expected by config/test_config.yaml
    store.write_metadata(
        run_dir,
        {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "test_duration": cfg.sampling.total_duration_seconds,
            "sampling_frequency": cfg.sampling.sampling_frequency_hz,
            "ammeter_type": ",".join([a.name for a in cfg.ammeters]),
        },
    )

    # Plots (bonus)
    if cfg.analysis.visualization.enabled:
        render_plots(measurements, cfg.analysis.visualization.plot_types, run_dir / "plots")

    return run_dir
