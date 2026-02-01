from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .unified_api import Measurement


@dataclass(frozen=True)
class Stats:
    count: int
    ok_count: int
    mean: Optional[float]
    median: Optional[float]
    std_dev: Optional[float]
    min: Optional[float]
    max: Optional[float]


def compute_stats(values: List[float]) -> Stats:
    if not values:
        return Stats(count=0, ok_count=0, mean=None, median=None, std_dev=None, min=None, max=None)

    mean_v = statistics.fmean(values)
    median_v = statistics.median(values)
    std_v = statistics.pstdev(values) if len(values) >= 2 else 0.0
    return Stats(
        count=len(values),
        ok_count=len(values),
        mean=mean_v,
        median=median_v,
        std_dev=std_v,
        min=min(values),
        max=max(values),
    )


def split_by_ammeter(measurements: List[Measurement]) -> Dict[str, List[Measurement]]:
    out: Dict[str, List[Measurement]] = {}
    for m in measurements:
        out.setdefault(m.ammeter, []).append(m)
    return out


def stats_by_ammeter(measurements: List[Measurement]) -> Dict[str, Stats]:
    by = split_by_ammeter(measurements)
    ret: Dict[str, Stats] = {}
    for name, ms in by.items():
        vals = [m.value_a for m in ms if m.ok and m.value_a is not None]
        s = compute_stats(vals)
        # Count total + ok
        ret[name] = Stats(
            count=len(ms),
            ok_count=len(vals),
            mean=s.mean,
            median=s.median,
            std_dev=s.std_dev,
            min=s.min,
            max=s.max,
        )
    return ret


@dataclass(frozen=True)
class Agreement:
    mae: Optional[float]
    rmse: Optional[float]
    correlation: Optional[float]
    paired_count: int


def _pearson(x: List[float], y: List[float]) -> Optional[float]:
    if len(x) < 2 or len(y) < 2:
        return None
    mx = statistics.fmean(x)
    my = statistics.fmean(y)
    num = sum((a - mx) * (b - my) for a, b in zip(x, y))
    denx = math.sqrt(sum((a - mx) ** 2 for a in x))
    deny = math.sqrt(sum((b - my) ** 2 for b in y))
    if denx == 0 or deny == 0:
        return None
    return num / (denx * deny)


def pairwise_agreement(measurements: List[Measurement]) -> Dict[Tuple[str, str], Agreement]:
    """Compute agreement between ammeters.

    We pair measurements by sample index: since the sampler collects values in a fixed order per tick,
    we can align them by ordering.
    """

    by = split_by_ammeter(measurements)
    names = sorted(by.keys())
    out: Dict[Tuple[str, str], Agreement] = {}

    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a = names[i]
            b = names[j]
            xs = [m.value_a for m in by[a] if m.ok and m.value_a is not None]
            ys = [m.value_a for m in by[b] if m.ok and m.value_a is not None]
            n = min(len(xs), len(ys))
            xs = xs[:n]
            ys = ys[:n]
            if n == 0:
                out[(a, b)] = Agreement(mae=None, rmse=None, correlation=None, paired_count=0)
                continue
            diffs = [abs(x - y) for x, y in zip(xs, ys)]
            mae = statistics.fmean(diffs)
            rmse = math.sqrt(statistics.fmean([(x - y) ** 2 for x, y in zip(xs, ys)]))
            corr = _pearson(xs, ys)
            out[(a, b)] = Agreement(mae=mae, rmse=rmse, correlation=corr, paired_count=n)
    return out


def reliability_ranking(stats: Dict[str, Stats], agreements: Dict[Tuple[str, str], Agreement]) -> List[str]:
    """Heuristic ranking (bonus).

    Since we do not have ground truth, we score each ammeter by:
      - success rate (ok/total)
      - lower std_dev (more stable)
      - lower average pairwise rmse vs others (more "agreeable")
    """

    names = list(stats.keys())
    scores: Dict[str, float] = {n: 0.0 for n in names}
    for n, s in stats.items():
        success = (s.ok_count / s.count) if s.count else 0.0
        stability = 1.0 / (1.0 + (s.std_dev or 0.0))
        scores[n] += 2.0 * success + stability

    # Agreement penalty
    for (a, b), ag in agreements.items():
        if ag.rmse is None:
            continue
        scores[a] += 1.0 / (1.0 + ag.rmse)
        scores[b] += 1.0 / (1.0 + ag.rmse)

    return sorted(names, key=lambda n: scores[n], reverse=True)
