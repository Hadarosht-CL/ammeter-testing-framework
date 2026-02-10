"""
Configuration-driven ammeter testing framework.

This test demonstrates:
- Getting config path from command line arguments (--config)
- Using sample_quick.yaml as default if no config provided
- Parsing the configuration file
- Running the project framework
- Saving results
- Reporting measurement errors at the end of the test

Usage:
  # Using unittest with default config
  python -m unittest tests.test_config_driven -v

  # Using the wrapper script with default config
  python run_config_test.py -v

  # Using the wrapper script with custom config
  python run_config_test.py --config configs/sample_quick.yaml -v
  python run_config_test.py --config configs/scenario_fault_injection.yaml -v
  python run_config_test.py --config configs/scenario_duration_based.yaml -v
  python run_config_test.py --config configs/scenario_datadog.yaml -v
"""

import json
import os
import time
import unittest
from pathlib import Path
from collections import defaultdict

from Ammeters.Circutor_Ammeter import CircutorAmmeter
from Ammeters.Entes_Ammeter import EntesAmmeter
from Ammeters.Greenlee_Ammeter import GreenleeAmmeter

from framework.config_loader import load_yaml, parse_config
from framework.runner import run_project

INIT_DELAY_SECONDS = 0.8

CIRCUTOR_EMULATOR_NAME = "circutor"
ENTES_EMULATOR_NAME = "entes"
GREENLEE_EMULATOR_NAME = "greenlee"

class TestConfigDrivenFramework(unittest.TestCase):
    """Test the framework with configuration loaded from a YAML file."""

    @classmethod
    def setUpClass(cls):
        """Get config path from environment variable or use default."""
        config_path = os.environ.get("AMMETER_TEST_CONFIG", "configs/sample_quick.yaml")
        cls.config_path = Path(config_path)

    @staticmethod
    def _analyze_and_report_errors(measurements_file: Path) -> None:
        """
        Load measurements from JSON file and report any errors to console.
        
        Args:
            measurements_file: Path to the measurements.json file
        """
        if not measurements_file.exists():
            return
        
        try:
            with measurements_file.open("r", encoding="utf-8") as f:
                measurements = json.load(f)
        except (json.JSONDecodeError, IOError):
            return
        
        # Collect error statistics
        error_count = 0
        error_by_type = defaultdict(int)
        error_by_ammeter = defaultdict(int)
        failed_measurements = []
        
        for i, measurement in enumerate(measurements):
            if not measurement.get("ok", True):
                error_count += 1
                error_type = measurement.get("error", "unknown")
                ammeter = measurement.get("ammeter", "unknown")
                
                error_by_type[error_type] += 1
                error_by_ammeter[ammeter] += 1
                
                failed_measurements.append({
                    "index": i,
                    "ammeter": ammeter,
                    "error": error_type,
                    "timestamp": measurement.get("wall_time_epoch"),
                    "latency_s": measurement.get("latency_s"),
                })
        
        # Print error report to console if there are errors
        if error_count > 0:
            print("\n" + "=" * 80)
            print("⚠️  MEASUREMENT ERROR REPORT")
            print("=" * 80)
            
            print(f"\n📊 SUMMARY:")
            print(f"   Total Errors: {error_count} / {len(measurements)} measurements")
            print(f"   Error Rate: {100.0 * error_count / len(measurements):.2f}%")
            
            print(f"\n📈 ERRORS BY TYPE:")
            for error_type in sorted(error_by_type.keys()):
                count = error_by_type[error_type]
                percentage = 100.0 * count / error_count
                print(f"   - {error_type}: {count} ({percentage:.1f}%)")
            
            print(f"\n🔧 ERRORS BY AMMETER:")
            for ammeter in sorted(error_by_ammeter.keys()):
                count = error_by_ammeter[ammeter]
                percentage = 100.0 * count / error_count
                print(f"   - {ammeter}: {count} ({percentage:.1f}%)")
            
            print(f"\n📋 DETAILED ERRORS (first 20):")
            for measurement in failed_measurements[:20]:
                print(f"   [{measurement['index']:3d}] {measurement['ammeter']:10s} "
                      f"error={measurement['error']:15s} latency={measurement['latency_s']:.3f}s")
            
            if len(failed_measurements) > 20:
                print(f"   ... and {len(failed_measurements) - 20} more errors")
            
            print("\n" + "=" * 80 + "\n")

    def test_config_driven_framework(self):

        # Step 1: Verify config file exists
        self.assertTrue(
            self.config_path.exists(),
            f"Config file not found: {self.config_path}",
        )

        # Start ammeters based on the ports in the config
        loaded_config = load_yaml(self.config_path)
        parsed_config = parse_config(loaded_config)

        # Extract ports from config
        ports = {}
        for ammeter in parsed_config.ammeters:
            ports[ammeter.name] = ammeter.port

        # Start emulators in separate threads
        import threading
        threading.Thread(target=GreenleeAmmeter(ports[GREENLEE_EMULATOR_NAME]).start_server, daemon=True).start()
        threading.Thread(target=EntesAmmeter(ports[ENTES_EMULATOR_NAME]).start_server, daemon=True).start()
        threading.Thread(target=CircutorAmmeter(ports[CIRCUTOR_EMULATOR_NAME]).start_server, daemon=True).start()
        time.sleep(INIT_DELAY_SECONDS)

        # Verify that ports are from the config
        for ammeter in parsed_config.ammeters:
            self.assertIn(ammeter.name, ports)
            self.assertEqual(ammeter.port, ports[ammeter.name])

        # Verify sampling configuration is loaded
        self.assertIsNotNone(parsed_config.sampling)
        self.assertIsNotNone(parsed_config.sampling.sampling_frequency_hz)

        # Step 3: Run the project
        run_dir = run_project(parsed_config, loaded_config)

        # Step 4: Verify results were saved
        self.assertTrue(
            run_dir.exists(),
            f"Run directory should exist: {run_dir}",
        )

        self.assertTrue(
            (run_dir / "summary.json").exists(),
            "Summary file should be created",
        )

        self.assertTrue(
            (run_dir / "measurements.json").exists(),
            "Measurements file should be created",
        )

        # Check if visualization is enabled and plots were created
        if parsed_config.analysis.visualization.enabled:
            plots_dir = run_dir / "plots"
            self.assertTrue(
                plots_dir.exists(),
                "Plots directory should be created when visualization is enabled",
            )
            # Check that at least one plot file exists
            plot_files = list(plots_dir.glob("*.png"))
            self.assertTrue(
                len(plot_files) > 0,
                "At least one plot file should be generated",
            )

        # Verify results are saved in the configured format
        save_format = parsed_config.results.save_format
        if save_format == "json":
            self.assertTrue(
                (run_dir / "measurements.json").exists(),
                "Measurements should be saved in JSON format",
            )
        
        # Analyze and report any measurement errors at the end
        measurements_file = run_dir / "measurements.json"
        self._analyze_and_report_errors(measurements_file)


if __name__ == "__main__":
    unittest.main()
