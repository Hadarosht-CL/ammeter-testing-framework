"""
Utility functions for configuration management and random data generation.
"""

import random
from pathlib import Path
from typing import Dict, Tuple
import yaml


CONFIG_PATH = "config/test_config.yaml"
DEFAULTS = {
    "greenlee": {"port": 5000, "command": b"MEASURE_GREENLEE -get_measurement"},
    "entes": {"port": 5001, "command": b"MEASURE_ENTES -get_data"},
    "circutor": {"port": 5002, "command": b"MEASURE_CIRCUTOR -get_measurement"},
}


def generate_random_float(min_value: float, max_value: float) -> float:
    """Generate a random float between min_value and max_value."""
    return random.uniform(min_value, max_value)


def get_config_path() -> Path:
    return Path(__file__).parent.parent / CONFIG_PATH


def load_config(path: Path) -> Dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
    

def resolve_ports_and_commands(cfg: Dict) -> Dict[str, Tuple[int, bytes]]:
    result: Dict[str, Tuple[int, bytes]] = {}
    ammeters_cfg = (cfg or {}).get("ammeters", {})
    for key in ("greenlee", "entes", "circutor"):
        port = int(ammeters_cfg.get(key, {}).get("port", DEFAULTS[key]["port"]))
        cmd = ammeters_cfg.get(key, {}).get("command", DEFAULTS[key]["command"].decode("utf-8"))
        result[key] = (port, cmd.encode("utf-8"))
    return result