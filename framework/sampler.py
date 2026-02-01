from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

from .config_loader import SamplingCfg
from .datadog_metrics import DogStatsd
from .faults import FaultInjector
from .unified_api import AmmeterClient, Measurement


@dataclass(frozen=True)
class SampleBatch:
    measurements: List[Measurement]


class Sampler:
    """Real-time-ish sampler.

    Uses time.monotonic() scheduling to reduce drift.
    """

    def __init__(
        self,
        clients: List[AmmeterClient],
        sampling: SamplingCfg,
        fault_injector: Optional[FaultInjector] = None,
        dd: Optional[DogStatsd] = None,
    ):
        if sampling.sampling_frequency_hz <= 0:
            raise ValueError("sampling_frequency_hz must be > 0")
        self.clients = clients
        self.sampling = sampling
        self.period_s = 1.0 / sampling.sampling_frequency_hz
        self.faults = fault_injector
        self.dd = dd

    def run(self) -> List[Measurement]:
        out: List[Measurement] = []
        t_start = time.monotonic()
        n = 0

        while True:
            # Stop conditions
            if self.sampling.measurements_count is not None and n >= int(self.sampling.measurements_count):
                break
            if self.sampling.total_duration_seconds is not None:
                if (time.monotonic() - t_start) >= float(self.sampling.total_duration_seconds):
                    break

            target_t = t_start + n * self.period_s
            now = time.monotonic()
            sleep_s = target_t - now
            if sleep_s > 0:
                time.sleep(sleep_s)

            # Collect one reading per ammeter per "tick"
            for c in self.clients:
                m = c.measure()
                if self.faults:
                    m = self.faults.apply(m)

                out.append(m)

                # DataDog metrics (optional)
                if self.dd:
                    tags = {"ammeter": m.ammeter}
                    if m.ok and m.value_a is not None:
                        self.dd.gauge("current_a", m.value_a, tags=tags)
                        self.dd.increment("measure_ok", tags=tags)
                    else:
                        self.dd.increment("measure_error", tags=tags)
                    self.dd.timing("latency_ms", m.latency_s * 1000.0, tags=tags)

            n += 1

        return out
