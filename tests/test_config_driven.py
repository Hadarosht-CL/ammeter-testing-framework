"""
Configuration-driven ammeter testing framework.

This test demonstrates:
- Getting config path from command line arguments (--config)
- Using sample_quick.yaml as default if no config provided
- Parsing the configuration file
- Running the project framework
- Saving results

Usage:
  python -m unittest tests.test_config_driven -v
  python -m unittest tests.test_config_driven -v -- --config configs/sample_quick.yaml
  python -m unittest tests.test_config_driven -v -- --config configs/scenario_fault_injection.yaml
"""

import argparse
import sys
import time
import unittest
from pathlib import Path

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
        """Parse command-line arguments and get the config path."""
        # Remove unittest's test arguments to avoid conflicts
        parser = argparse.ArgumentParser(description="Ammeter Testing Framework")
        parser.add_argument(
            "--config",
            type=str,
            default="configs/sample_quick.yaml",
            help="Path to the configuration file (default: configs/sample_quick.yaml)",
        )

        # Filter out unittest arguments
        custom_args = [
            arg for arg in sys.argv[1:]
            if arg not in ["-v", "-q", "--verbose", "--help", "-h"]
            and not arg.startswith("tests.")
        ]

        args, _ = parser.parse_known_args(custom_args)
        cls.config_path = Path(args.config)

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


if __name__ == "__main__":
    unittest.main()
