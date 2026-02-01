from __future__ import annotations

import socket
import time
from dataclasses import dataclass
from typing import Dict, Iterable, Optional

from .config_loader import DatadogCfg


class DogStatsd:
    """Minimal DogStatsD client (UDP) with zero external dependencies.

    If the agent isn't running, packets are dropped and the framework continues.
    """

    def __init__(self, cfg: DatadogCfg):
        self.cfg = cfg
        self.addr = (cfg.host, cfg.port)
        self.namespace = cfg.namespace.rstrip(".")
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def _fmt(self, name: str) -> str:
        return f"{self.namespace}.{name}" if self.namespace else name

    def _send(self, msg: str) -> None:
        try:
            self._sock.sendto(msg.encode("utf-8"), self.addr)
        except Exception:
            # Never fail tests due to monitoring.
            return

    def gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        self._send(self._metric(name, value, "g", tags))

    def increment(self, name: str, value: int = 1, tags: Optional[Dict[str, str]] = None) -> None:
        self._send(self._metric(name, value, "c", tags))

    def timing(self, name: str, value_ms: float, tags: Optional[Dict[str, str]] = None) -> None:
        self._send(self._metric(name, value_ms, "ms", tags))

    def _metric(self, name: str, value, mtype: str, tags: Optional[Dict[str, str]]) -> str:
        metric = f"{self._fmt(name)}:{value}|{mtype}"
        if tags:
            # dogstatsd tags format: |#tag1:value,tag2:value
            t = ",".join([f"{k}:{v}" for k, v in tags.items()])
            metric += f"|#{t}"
        return metric


def maybe_create_client(cfg: DatadogCfg) -> Optional[DogStatsd]:
    return DogStatsd(cfg) if cfg.enabled else None
