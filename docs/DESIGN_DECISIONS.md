# Design decisions

This document briefly explains architectural choices and required fixes.

## Why keep emulator infra intact

The assignment requires using the provided emulator infrastructure. Instead of replacing it,
we made minimal, targeted fixes:

1) **Port mismatch** – starter `main.py` used 5001–5003 while README/config use 5000–5002.
   `main.py` now loads ports from `config/test_config.yaml`.

2) **CIRCUTOR command mismatch** – README/config use `MEASURE_CIRCUTOR -get_measurement` but the
   emulator expected `MEASURE_CIRCUTOR -get_measurement -current`.
   The emulator now uses the README/config command as canonical and supports the legacy alias.

3) **Silent failure on bad commands** – the base server used to send nothing.
   It now returns `ERROR: Unsupported command` for clearer error handling.

## Unified measurement API

`framework.unified_api.AmmeterClient` wraps socket communication and returns a structured `Measurement`:
- value (float in Amperes)
- latency (seconds)
- ok/error
- timestamps

This makes tests independent of the particular emulator protocol details.

## Sampling strategy

Sampling is scheduled using `time.monotonic()` to reduce drift:
- each tick is scheduled at `start + n * period`
- the loop sleeps only the difference between now and the target

This is the standard way to approximate real-time periodic tasks in user-space Python.

## No “absolute accuracy” without ground truth

The assignment asks for "accuracy assessment" as a bonus. Since we don't have a ground-truth sensor,
the framework implements **relative** accuracy as agreement between instruments:
- pairwise MAE/RMSE
- correlation
- a heuristic “reliability ranking” based on success rate, stability (std dev), and agreement.

## DataDog integration without extra dependencies

To satisfy monitoring requirements while minimizing dependencies, the framework includes a small UDP DogStatsD
client. If the agent isn't available, metrics are simply dropped and tests do not fail.

## `allowed_commands` vs `get_current_command`

The emulator classes define `get_current_command` as the single **canonical** command (the official command string that the README/config specify).

`allowed_commands()` exists only to support **backward-compatible aliases** (e.g., the starter `main.py` sending a shortened command like `MEASURE_GREENLEE`). By default, the base class implementation returns just `[self.get_current_command]`, and each ammeter overrides it to add legacy aliases when needed.
