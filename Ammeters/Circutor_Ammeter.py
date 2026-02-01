from Ammeters.base_ammeter import AmmeterEmulatorBase
from Utiles.Utils import generate_random_float


class CircutorAmmeter(AmmeterEmulatorBase):
    @property
    def get_current_command(self) -> bytes:
        # Canonical command (matches README + config/test_config.yaml)
        return b'MEASURE_CIRCUTOR -get_measurement'

    def allowed_commands(self):
        # Backward-compatible alias used in the buggy starter code.
        return [
            self.get_current_command,
            b"MEASURE_CIRCUTOR",
            b"MEASURE_CIRCUTOR -get_measurement -current",
        ]

    def measure_current(self) -> float:
        num_samples = 10
        time_step = generate_random_float(0.001, 0.01)  # Time step (0.001s - 0.01s)
        voltages = [generate_random_float(0.1, 1.0) for _ in range(num_samples)]  # Voltage values

        print(f"CIRCUTOR Ammeter - Voltages: {voltages}, Time Step: {time_step}s")
        current = sum(v * time_step for v in voltages)
        print(f"Current: {current}A")
        return current
