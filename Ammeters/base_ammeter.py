import socket
import time
import random
from abc import ABC, abstractmethod
from typing import List


NotImplementedErrorMsg = "Subclasses must implement this property."


class AmmeterEmulatorBase(ABC):
    """TCP ammeter emulator base.

    The exercise provides three emulator implementations. This base class is slightly
    hardened to:
      * allow quick restarts (SO_REUSEADDR)
      * avoid silent failures (return ERROR on unknown commands)
      * keep backward-compatibility via command aliases
    """

    def __init__(self, port: int, host: str = "localhost"):
        self.host = host
        self.port = int(port)
        random.seed(time.time())  # Seed RNG per instance

    def allowed_commands(self) -> List[bytes]:
        """Commands the emulator accepts.

        By default it's just the canonical get_current_command.
        Subclasses may override to include legacy aliases.
        """

        return [self.get_current_command]

    def start_server(self):
        """
        Starts the server to listen for client requests.
        The server runs indefinitely, handling one client request at a time.
        """

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((self.host, self.port))
            s.listen()
            print(f"{self.__class__.__name__} is running on {self.host}:{self.port}")
            while True:
                conn, addr = s.accept()
                with conn:
                    data = conn.recv(1024)
                    if not data:
                        continue

                    if data in self.allowed_commands():
                        current = self.measure_current()
                        conn.sendall(str(current).encode("utf-8"))
                    else:
                        # Previously the infra returned nothing; that caused clients to hang / get empty reads.
                        conn.sendall(b"ERROR: Unsupported command")

    @property
    @abstractmethod
    def get_current_command(self) -> bytes:
        """Canonical command to request a current measurement."""
        raise NotImplementedError(NotImplementedErrorMsg)

    @abstractmethod
    def measure_current(self) -> float:
        """Generate a simulated current measurement."""
        raise NotImplementedError(NotImplementedErrorMsg)
