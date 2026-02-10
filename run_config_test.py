#!/usr/bin/env python
"""
Wrapper script to run the config-driven test with custom configuration.

Usage:
    python run_config_test.py                                          # Use default config
    python run_config_test.py --config configs/sample_quick.yaml      # Explicit default
    python run_config_test.py --config configs/scenario_fault_injection.yaml  # Custom config
"""

import argparse
import sys
import os
import unittest

def main():
    parser = argparse.ArgumentParser(description="Run config-driven ammeter test")
    parser.add_argument(
        "--config",
        type=str,
        default="configs/sample_quick.yaml",
        help="Path to the configuration file (default: configs/sample_quick.yaml)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output",
    )
    
    args = parser.parse_args()
    
    # Store config path in environment variable
    os.environ["AMMETER_TEST_CONFIG"] = args.config
    
    # Build unittest arguments
    unittest_args = ["discover", "-s", "tests", "-p", "test_config_driven.py"]
    if args.verbose:
        unittest_args.insert(0, "-v")
    
    # Run unittest
    loader = unittest.TestLoader()
    suite = loader.discover("tests", pattern="test_config_driven.py")
    runner = unittest.TextTestRunner(verbosity=2 if args.verbose else 1)
    result = runner.run(suite)
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)

if __name__ == "__main__":
    main()
