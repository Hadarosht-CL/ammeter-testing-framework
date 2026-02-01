from __future__ import annotations

import time
from dataclasses import dataclass
from socket import socket, AF_INET, SOCK_STREAM
from typing import Optional


@dataclass(frozen=True)
class Measurement:
    ammeter: str
    timestamp_monotonic: float
    wall_time_epoch: float
    value_a: Optional[float]
    latency_s: float
    ok: bool
    error: Optional[str] = None


class AmmeterClient:
    """Unifies communication with the different emulator types."""

    def __init__(self, name: str, host: str, port: int, command: bytes, timeout_s: float = 2.0):
        self.name = name
        self.host = host
        self.port = int(port)
        self.command = command
        self.timeout_s = float(timeout_s)

    def measure(self) -> Measurement:
        t0 = time.monotonic()
        epoch = time.time()
        try:
            with socket(AF_INET, SOCK_STREAM) as s:
                s.settimeout(self.timeout_s)
                s.connect((self.host, self.port))
                s.sendall(self.command)
                data = s.recv(1024)

            if not data:
                return Measurement(
                    ammeter=self.name,
                    timestamp_monotonic=t0,
                    wall_time_epoch=epoch,
                    value_a=None,
                    latency_s=time.monotonic() - t0,
                    ok=False,
                    error="no_data",
                )

            resp = data.decode("utf-8", errors="replace").strip()
            if resp.startswith("ERROR:"):
                return Measurement(
                    ammeter=self.name,
                    timestamp_monotonic=t0,
                    wall_time_epoch=epoch,
                    value_a=None,
                    latency_s=time.monotonic() - t0,
                    ok=False,
                    error=resp,
                )

            value = float(resp)
            return Measurement(
                ammeter=self.name,
                timestamp_monotonic=t0,
                wall_time_epoch=epoch,
                value_a=value,
                latency_s=time.monotonic() - t0,
                ok=True,
            )
        except Exception as e:  # noqa: BLE001
            return Measurement(
                ammeter=self.name,
                timestamp_monotonic=t0,
                wall_time_epoch=epoch,
                value_a=None,
                latency_s=time.monotonic() - t0,
                ok=False,
                error=repr(e),
            )
