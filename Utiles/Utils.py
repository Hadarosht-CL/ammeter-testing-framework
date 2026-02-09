"""
Utility functions for configuration management and random data generation.
"""

import random
from pathlib import Path
from typing import Any, Dict, Tuple
import yaml


CONFIG_PATH = "config/test_config.yaml"
DEFAULTS = {
    "greenlee": {"port": 5000, "command": b"MEASURE_GREENLEE -get_measurement"},
    "entes": {"port": 5001, "command": b"MEASURE_ENTES -get_data"},
    "circutor": {"port": 5002, "command": b"MEASURE_CIRCUTOR -get_measurement"},
}

# Config helpers
def load_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Config must be a mapping/dict. Got: {type(data)}")
    return data


def validate_config_schema(cfg: Dict[str, Any]) -> None:
    # Minimal validation aligned with your README schema
    if "ammeters" not in cfg or not isinstance(cfg["ammeters"], dict):
        raise ValueError("Config must contain 'ammeters:' mapping")

    if "testing" not in cfg or not isinstance(cfg["testing"], dict):
        raise ValueError("Config must contain 'testing:' mapping")
    if "sampling" not in cfg["testing"] or not isinstance(cfg["testing"]["sampling"], dict):
        raise ValueError("Config must contain 'testing.sampling:' mapping")

    sampling = cfg["testing"]["sampling"]
    if "sampling_frequency_hz" not in sampling:
        raise ValueError("Config must define testing.sampling.sampling_frequency_hz")

    # Must have stop condition: either count or duration
    if "measurements_count" not in sampling and "total_duration_seconds" not in sampling:
        raise ValueError("Config must define either measurements_count or total_duration_seconds")

    # Ammeter entries must have at least port + command
    for name, info in cfg["ammeters"].items():
        if not isinstance(info, dict):
            raise ValueError(f"ammeters.{name} must be a mapping")
        if "port" not in info:
            raise ValueError(f"ammeters.{name}.port missing")
        if "command" not in info:
            raise ValueError(f"ammeters.{name}.command missing")


def override_results_path(cfg: Dict[str, Any], results_dir: Path) -> Dict[str, Any]:
    """
    Forces result_management.save_path to a temp dir so the E2E test doesn't pollute repo results/.
    """
    cfg = dict(cfg)  # shallow copy
    rm = dict(cfg.get("result_management", {}))
    rm["save_path"] = str(results_dir)
    cfg["result_management"] = rm
    return cfg


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