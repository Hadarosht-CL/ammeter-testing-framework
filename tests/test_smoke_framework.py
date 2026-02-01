import tempfile
import time
import unittest
from pathlib import Path

import yaml

from Ammeters.Circutor_Ammeter import CircutorAmmeter
from Ammeters.Entes_Ammeter import EntesAmmeter
from Ammeters.Greenlee_Ammeter import GreenleeAmmeter

from framework.config_loader import load_yaml, parse_config
from framework.runner import run_project


class TestSmokeFramework(unittest.TestCase):
    def test_end_to_end(self):
        # Use non-default ports to avoid conflicts if user already runs main.py
        ports = {
            "greenlee": 6100,
            "entes": 6101,
            "circutor": 6102,
        }

        # Start emulators
        import threading

        threading.Thread(target=GreenleeAmmeter(ports["greenlee"]).start_server, daemon=True).start()
        threading.Thread(target=EntesAmmeter(ports["entes"]).start_server, daemon=True).start()
        threading.Thread(target=CircutorAmmeter(ports["circutor"]).start_server, daemon=True).start()
        time.sleep(0.8)

        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            cfg_path = td / "cfg.yaml"
            out_dir = td / "results"
            raw = {
                "testing": {
                    "sampling": {
                        "measurements_count": 5,
                        "total_duration_seconds": None,
                        "sampling_frequency_hz": 5,
                    }
                },
                "ammeters": {
                    "greenlee": {"port": ports["greenlee"], "command": "MEASURE_GREENLEE -get_measurement"},
                    "entes": {"port": ports["entes"], "command": "MEASURE_ENTES -get_data"},
                    "circutor": {"port": ports["circutor"], "command": "MEASURE_CIRCUTOR -get_measurement"},
                },
                "analysis": {
                    "statistical_metrics": ["mean", "median", "std_dev", "min", "max"],
                    "visualization": {"enabled": True, "plot_types": ["time_series"]},
                },
                "result_management": {
                    "save_path": str(out_dir),
                    "save_format": "json",
                    "metadata_fields": ["timestamp"],
                },
            }

            cfg_path.write_text(yaml.safe_dump(raw), encoding="utf-8")

            loaded = load_yaml(cfg_path)
            cfg = parse_config(loaded)
            run_dir = run_project(cfg, loaded)

            self.assertTrue((run_dir / "summary.json").exists())
            self.assertTrue((run_dir / "measurements.json").exists())
            self.assertTrue((run_dir / "plots" / "time_series.png").exists())


if __name__ == "__main__":
    unittest.main()
