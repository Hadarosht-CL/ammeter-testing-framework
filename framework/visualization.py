from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import matplotlib.pyplot as plt

from .unified_api import Measurement
from .analysis import split_by_ammeter


def _series_by_ammeter(measurements: List[Measurement]) -> Dict[str, List[float]]:
    by = split_by_ammeter(measurements)
    out: Dict[str, List[float]] = {}
    for name, ms in by.items():
        out[name] = [m.value_a for m in ms if m.ok and m.value_a is not None]
    return out


def plot_time_series(measurements: List[Measurement], out_dir: Path) -> None:
    series = _series_by_ammeter(measurements)
    if not series or all(len(vals) == 0 for vals in series.values()):
        return
    out_dir.mkdir(parents=True, exist_ok=True)
    plt.figure()
    for name, vals in series.items():
        plt.plot(list(range(len(vals))), vals, label=name)
    plt.xlabel("sample")
    plt.ylabel("current (A)")
    plt.title("Current over time")
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_dir / "time_series.png")
    plt.close()


def plot_histogram(measurements: List[Measurement], out_dir: Path) -> None:
    series = _series_by_ammeter(measurements)
    if not series or all(len(vals) == 0 for vals in series.values()):
        return
    out_dir.mkdir(parents=True, exist_ok=True)
    plt.figure()
    for name, vals in series.items():
        if vals:
            plt.hist(vals, bins=30, alpha=0.5, label=name)
    plt.xlabel("current (A)")
    plt.ylabel("count")
    plt.title("Histogram")
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_dir / "histogram.png")
    plt.close()


def plot_box(measurements: List[Measurement], out_dir: Path) -> None:
    series = _series_by_ammeter(measurements)
    if not series or all(len(vals) == 0 for vals in series.values()):
        return
    out_dir.mkdir(parents=True, exist_ok=True)
    names = list(series.keys())
    vals = [series[n] for n in names]
    plt.figure()
    plt.boxplot(vals, labels=names, showfliers=True)
    plt.ylabel("current (A)")
    plt.title("Box plot")
    plt.tight_layout()
    plt.savefig(out_dir / "box_plot.png")
    plt.close()


def render_plots(measurements: List[Measurement], plot_types: List[str], out_dir: Path) -> None:
    for p in plot_types:
        if p == "time_series":
            plot_time_series(measurements, out_dir)
        elif p == "histogram":
            plot_histogram(measurements, out_dir)
        elif p == "box_plot":
            plot_box(measurements, out_dir)
