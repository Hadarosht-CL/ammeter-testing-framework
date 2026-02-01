from socket import socket, AF_INET, SOCK_STREAM


def request_current_from_ammeter(port: int, command: bytes, host: str = "localhost", timeout_s: float = 2.0):
    """Request a current measurement from a running emulator.

    Returns the raw response as a decoded string.
    """

    with socket(AF_INET, SOCK_STREAM) as s:
        s.settimeout(timeout_s)
        s.connect((host, port))
        s.sendall(command)
        data = s.recv(1024)
        if not data:
            msg = "No data received."
            print(msg)
            return msg

        response = data.decode("utf-8", errors="replace")
        if response.startswith("ERROR:"):
            print(f"Received error from port {port}: {response}")
        else:
            print(f"Received current measurement from port {port}: {response} A")
        return response

