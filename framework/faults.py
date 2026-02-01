from __future__ import annotations

import random
import time
from dataclasses import dataclass

from .config_loader import FaultInjectionCfg
from .unified_api import Measurement


class FaultInjector:
    """Applies fault injection to measurement results.

    This is implemented as a post-processing step so it doesn't alter the emulator infrastructure.
    """

    def __init__(self, cfg: FaultInjectionCfg):
        self.cfg = cfg

    def apply(self, m: Measurement) -> Measurement:
        if not self.cfg.enabled:
            return m

        # Drop: convert to a failed measurement
        if random.random() < self.cfg.drop_prob:
            return Measurement(
                ammeter=m.ammeter,
                timestamp_monotonic=m.timestamp_monotonic,
                wall_time_epoch=m.wall_time_epoch,
                value_a=None,
                latency_s=m.latency_s,
                ok=False,
                error="fault_drop",
            )

        # Delay (simulates slow communication): sleep after measurement
        if random.random() < self.cfg.delay_prob:
            delay_ms = random.randint(self.cfg.delay_ms_min, max(self.cfg.delay_ms_min, self.cfg.delay_ms_max))
            time.sleep(delay_ms / 1000.0)
            m = Measurement(
                ammeter=m.ammeter,
                timestamp_monotonic=m.timestamp_monotonic,
                wall_time_epoch=m.wall_time_epoch,
                value_a=m.value_a,
                latency_s=m.latency_s + (delay_ms / 1000.0),
                ok=m.ok,
                error=m.error,
            )

        # Corrupt: flip to invalid payload
        if random.random() < self.cfg.corrupt_prob:
            return Measurement(
                ammeter=m.ammeter,
                timestamp_monotonic=m.timestamp_monotonic,
                wall_time_epoch=m.wall_time_epoch,
                value_a=None,
                latency_s=m.latency_s,
                ok=False,
                error="fault_corrupt",
            )

        # Outlier: amplify the numeric value
        if m.ok and m.value_a is not None and random.random() < self.cfg.outlier_prob:
            return Measurement(
                ammeter=m.ammeter,
                timestamp_monotonic=m.timestamp_monotonic,
                wall_time_epoch=m.wall_time_epoch,
                value_a=m.value_a * self.cfg.outlier_scale,
                latency_s=m.latency_s,
                ok=True,
                error="fault_outlier",
            )

        return m
