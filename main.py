"""
Main script to start ammeter emulators and request measurements.

This script:
  1) loads ports/commands from config/test_config.yaml (if present)
  2) starts the 3 emulator servers in threads
  3) requests a single measurement from each ammeter and prints the returned value

Run:
  python main.py
"""


import threading
import time

from Ammeters.Circutor_Ammeter import CircutorAmmeter
from Ammeters.Entes_Ammeter import EntesAmmeter
from Ammeters.Greenlee_Ammeter import GreenleeAmmeter
from Ammeters.client import request_current_from_ammeter
from Utiles.Utils import load_config, resolve_ports_and_commands, get_config_path

SLEEP_TIME = 1.0

def run_greenlee_emulator(port: int):
    GreenleeAmmeter(port).start_server()


def run_entes_emulator(port: int):
    EntesAmmeter(port).start_server()


def run_circutor_emulator(port: int):
    CircutorAmmeter(port).start_server()


if __name__ == "__main__":
    cfg = load_config(get_config_path())
    setup = resolve_ports_and_commands(cfg)

    threading.Thread(target=run_greenlee_emulator, args=(setup["greenlee"][0],), daemon=True).start()
    threading.Thread(target=run_entes_emulator, args=(setup["entes"][0],), daemon=True).start()
    threading.Thread(target=run_circutor_emulator, args=(setup["circutor"][0],), daemon=True).start()

    # Give servers time to bind/listen
    time.sleep(SLEEP_TIME)

    print("\nRequesting one measurement from each emulator:\n")
    request_current_from_ammeter(setup["greenlee"][0], setup["greenlee"][1])
    request_current_from_ammeter(setup["entes"][0], setup["entes"][1])
    request_current_from_ammeter(setup["circutor"][0], setup["circutor"][1])
