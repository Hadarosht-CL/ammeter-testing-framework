# Ammeter Testing Framework

This repository contains **three TCP ammeter emulators** (Greenlee, ENTES, CIRCUTOR) and a
**Python/unittest-based testing framework** that samples current measurements in real time,
analyzes results, and saves artifacts.

## Quickstart

```bash
pip install -r requirements.txt

# Run the configuration-driven test with default config (sample_quick.yaml)
python run_config_test.py -v

# Run with custom configuration
python run_config_test.py --config configs/scenario_fault_injection.yaml -v

# Run with unittest directly (default config only)
python -m unittest tests.test_config_driven -v
```

## Configuration-Driven Test (`test_config_driven.py`)

The main test file is **`tests/test_config_driven.py`**, which provides a flexible configuration-driven testing approach. The test:

1. **Reads configuration** from a YAML file (via `--config` argument or defaults to `configs/sample_quick.yaml`)
2. **Starts ammeters** dynamically based on the config (ports, commands, hosts)
3. **Runs the testing framework** to collect measurements from all 3 ammeters
4. **Analyzes results** with statistical metrics and optional visualizations
5. **Reports measurement errors** at the end with detailed breakdown by type and ammeter

### Running the Test

#### Using the wrapper script (Recommended)

```bash
# Default configuration (15 measurements, no fault injection)
python run_config_test.py -v

# With custom configuration
python run_config_test.py --config configs/sample_quick.yaml -v
python run_config_test.py --config configs/scenario_fault_injection.yaml -v
python run_config_test.py --config configs/scenario_duration_based.yaml -v
python run_config_test.py --config configs/scenario_datadog.yaml -v
```

#### Using unittest directly

```bash
# Default configuration only
python -m unittest tests.test_config_driven -v
```

### Example Test Output

**With Fault Injection** - Displays measurement error report:
```
================================================================================
⚠️  MEASUREMENT ERROR REPORT
================================================================================

📊 SUMMARY:
   Total Errors: 9 / 150 measurements
   Error Rate: 6.00%

📈 ERRORS BY TYPE:
   - fault_drop: 9 (100.0%)

🔧 ERRORS BY AMMETER:
   - circutor: 1 (11.1%)
   - entes: 4 (44.4%)
   - greenlee: 4 (44.4%)

📋 DETAILED ERRORS (first 20):
   [ 34] entes      error=fault_drop      latency=0.000s
   [ 39] greenlee   error=fault_drop      latency=0.002s
   [ 42] greenlee   error=fault_drop      latency=0.001s
   ...

================================================================================
```

**Without Errors** - Clean test run, error report is not displayed.

## Available Configurations

The test supports multiple YAML configurations in the `configs/` directory:

| Config | Purpose | Key Features |
|--------|---------|--------------|
| `sample_quick.yaml` | Default, quick test | 15 measurements, plots enabled, no faults |
| `scenario_fault_injection.yaml` | Test error handling | 150 measurements with fault injection (drop, corrupt) |
| `scenario_duration_based.yaml` | Time-based sampling | Run for 10 seconds instead of fixed count |
| `scenario_datadog.yaml` | Monitoring integration | DogStatsD metrics reporting (requires local agent) |

## Framework Architecture

The framework is **configuration-driven**:

- **Unified API**: `framework.unified_api.AmmeterClient` returns a structured `Measurement` object
- **Sampling**: `framework.sampler.Sampler` supports `measurements_count` and/or `total_duration_seconds` at a defined `sampling_frequency_hz`
- **Analysis**: Computes statistical metrics (mean, median, std_dev, min, max) and pairwise agreement between ammeters
- **Results**: Saves per-run results in a timestamped folder containing:
  - `config.json` – configuration snapshot
  - `measurements.json` – raw measurement data (with error status)
  - `summary.json` – statistical analysis and reliability ranking
  - `metadata.json` – test metadata
  - `plots/` – visualizations (time series, histogram, box plot)

## Error Reporting

The test automatically detects and reports measurement failures:

- **Error Detection**: Identifies measurements marked as `ok=false`
- **Categorization**: Groups errors by type (fault_drop, fault_corrupt, timeout, no_data, etc.)
- **Breakdown**: Shows distribution across ammeters
- **Details**: Lists first 20 failed measurements with indices, ammeter, error type, and latency
- **Smart Display**: Only shows report when errors are detected

## Configuration Format

Each YAML config file specifies:

```yaml
testing:
  sampling:
    measurements_count: 15           # Number of measurements (or null for duration-based)
    total_duration_seconds: null     # Total duration (or null for count-based)
    sampling_frequency_hz: 5         # Frequency of sampling

ammeters:
  greenlee:
    port: 5000
    command: "MEASURE_GREENLEE -get_measurement"
  entes:
    port: 5001
    command: "MEASURE_ENTES -get_data"
  circutor:
    port: 5002
    command: "MEASURE_CIRCUTOR -get_measurement"

analysis:
  statistical_metrics:
    - mean
    - median
    - std_dev
    - min
    - max
  visualization:
    enabled: true
    plot_types:
      - time_series
      - histogram
      - box_plot

result_management:
  save_path: "results/"
  save_format: "json"
  metadata_fields:
    - timestamp
    - ammeter_type
    - test_duration
    - sampling_frequency

# Optional: Fault injection simulation
fault_injection:
  enabled: false
  drop_prob: 0.05           # Probability of dropping a measurement
  delay_prob: 0.05          # Probability of adding delay
  delay_ms_min: 10
  delay_ms_max: 200
  corrupt_prob: 0.01        # Probability of corrupting a measurement
  outlier_prob: 0.01        # Probability of outlier values
  outlier_scale: 5.0

# Optional: DataDog monitoring
datadog:
  enabled: false
  host: "127.0.0.1"
  port: 8125
  namespace: "ammeter_test"
```

## Project Structure

```
├── Ammeters/                    # Ammeter emulators
│   ├── base_ammeter.py
│   ├── Greenlee_Ammeter.py
│   ├── Entes_Ammeter.py
│   ├── Circutor_Ammeter.py
│   └── client.py
├── framework/                   # Core testing framework
│   ├── config_loader.py
│   ├── runner.py
│   ├── sampler.py
│   ├── analysis.py
│   ├── unified_api.py
│   ├── result_store.py
│   ├── visualization.py
│   ├── faults.py
│   └── datadog_metrics.py
├── configs/                     # Configuration files
│   ├── sample_quick.yaml
│   ├── scenario_fault_injection.yaml
│   ├── scenario_duration_based.yaml
│   └── scenario_datadog.yaml
├── tests/                       # Test files
│   ├── test_config_driven.py    # Main configuration-driven test
│   └── test_smoke_framework.py  # Legacy smoke test
├── run_config_test.py           # Wrapper script for running test_config_driven
└── main.py                      # Simple demo that starts emulators and prints measurements
```

## Dependencies

```bash
pip install -r requirements.txt
```

The framework minimizes external dependencies:
- `pyyaml` – configuration parsing
- `matplotlib` – visualization (time series, histogram, box plot)

All other functionality uses Python's standard library.

## Emulator Protocol

Each emulator listens on a TCP port and returns a current value (in Amperes) as UTF-8 text:

| Ammeter | Default Port | Default Command |
|---------|-------------|-----------------|
| Greenlee | 5000 | `MEASURE_GREENLEE -get_measurement` |
| ENTES | 5001 | `MEASURE_ENTES -get_data` |
| CIRCUTOR | 5002 | `MEASURE_CIRCUTOR -get_measurement` |

The emulators are configurable via YAML to run on custom ports as shown in available configurations.
