# Submitter details:
Name: Hadar Rosht
Date: 30/01/2026

# Ammeter Testing Exercise (Embedded Systems QA)

This repository contains **three TCP ammeter emulators** (Greenlee, ENTES, CIRCUTOR) and a
**Python/unittest-based testing framework** that samples current measurements in real time,
analyzes results, and saves artifacts.

The implementation follows the provided assignment PDF. The PDF explicitly requires:
- **Read this README**
- **Make `main.py` work and return data from the ammeters**
- Build a unified measurement API, sampling, and analysis (with optional bonus items)

## Quickstart

```bash
pip install -r requirements.txt

# Required by the assignment: starts emulators and prints 3 current measurements
python main.py

# Run the full framework (config-driven)
python run_framework.py --config config/test_config.yaml

# Run unit tests (unittest discovery)
python -m unittest -v
```

**unittest discovery note:** `python -m unittest -v` discovers tests under `tests/` because `tests/` is a package (contains `__init__.py`).

## Example configurations

You can run different scenarios by pointing `run_framework.py` to one of the example YAML files:

```bash
# Short run with plots
python run_framework.py --config configs/sample_quick.yaml

# Stop by duration instead of count
python run_framework.py --config configs/scenario_duration_based.yaml

# Enable fault injection
python run_framework.py --config configs/scenario_fault_injection.yaml

# Enable DataDog DogStatsD metrics (requires a local agent)
python run_framework.py --config configs/scenario_datadog.yaml
```


## Project structure

- `Ammeters/` – emulator infrastructure (given + small fixes)
  - `base_ammeter.py` – TCP server base class
  - `Greenlee_Ammeter.py`, `Entes_Ammeter.py`, `Circutor_Ammeter.py`
  - `client.py` – minimal client helper
- `config/test_config.yaml` – configuration used by `main.py` and framework
- `framework/` – testing framework implementation
- `run_framework.py` – framework entrypoint
- `tests/` – unittest-based tests
- `docs/` – design notes

## Emulator protocol

Each emulator listens on a TCP port and replies with a single numeric current value encoded as UTF-8.

Default ports / commands (also in `config/test_config.yaml`):

| Ammeter | Port | Command |
|---|---:|---|
| Greenlee | 5000 | `MEASURE_GREENLEE -get_measurement` |
| ENTES | 5001 | `MEASURE_ENTES -get_data` |
| CIRCUTOR | 5002 | `MEASURE_CIRCUTOR -get_measurement` |

The emulators also accept legacy aliases used in the starter `main.py` (`MEASURE_GREENLEE`, etc.).

## What was fixed in the provided code (required by “use existing infrastructure”)

1) **`main.py` ports were wrong** (5001–5003). They did not match the README/config (5000–5002).
   - Fixed: `main.py` loads ports from `config/test_config.yaml` and starts emulators accordingly.

2) **CIRCUTOR command mismatch**
   - Starter code used `MEASURE_CIRCUTOR -get_measurement -current` but README/config require
     `MEASURE_CIRCUTOR -get_measurement`.
   - Fixed: canonical command is now the README/config command; legacy command remains accepted.

3) **Silent failure on unknown commands**
   - Previously, if a command didn’t match, the server sent nothing, causing clients to receive empty data.
   - Fixed: emulator replies with `ERROR: Unsupported command`.

## Framework overview

The framework is **configuration-driven**:

- **Unified API**: `framework.unified_api.AmmeterClient` returns a structured `Measurement` object.
- **Sampling**: `framework.sampler.Sampler` supports `measurements_count` and/or `total_duration_seconds`
  at a defined `sampling_frequency_hz`, using `time.monotonic()` scheduling.
- **Analysis**: `framework.analysis` computes mean/median/std/min/max and bonus pairwise agreement metrics.
- **Results**: `framework.result_store.ResultStore` creates a per-run folder containing:
  - `config.json`, `metadata.json`, `measurements.json|csv`, `summary.json`, `plots/`

### DataDog monitoring (optional)

If you run a local DogStatsD agent (default `127.0.0.1:8125`), enable in YAML:

```yaml
datadog:
  enabled: true
  host: 127.0.0.1
  port: 8125
  namespace: ammeter_test
```

The framework emits:
- `ammeter_test.current_a` (gauge)
- `ammeter_test.latency_ms` (timing)
- `ammeter_test.measure_ok` / `ammeter_test.measure_error` (counters)

No external `datadog` dependency is required.

### Fault injection (bonus)

Enable to simulate errors:

```yaml
fault_injection:
  enabled: true
  drop_prob: 0.05
  delay_prob: 0.05
  delay_ms_min: 10
  delay_ms_max: 200
  corrupt_prob: 0.01
  outlier_prob: 0.01
  outlier_scale: 10
```

## Dependencies

Install via `requirements.txt`:

```bash
pip install -r requirements.txt
```

To satisfy the PDF constraint *"Minimize external library dependencies"*, the framework uses only:
- `pyyaml` – configuration parsing
- `matplotlib` – basic plots (time series, histogram, box plot)

Everything else uses Python’s standard library.
