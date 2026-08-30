"""TICKETPASS/1.0 message encoding and parsing utilities."""

from dataclasses import dataclass

VERSION = "TICKETPASS/1.0"


@dataclass
class Message:
    start_line: str
    headers: dict[str, str]

    def to_bytes(self) -> bytes:
        lines = [self.start_line]
        lines.extend(f"{key}: {value}" for key, value in self.headers.items())
        return ("\r\n".join(lines) + "\r\n\r\n").encode("utf-8")


def request(command: str, **headers: object) -> Message:
    return Message(f"{VERSION} {command.upper()}", _clean_headers(headers))


def response(status_code: int, phrase: str, **headers: object) -> Message:
    return Message(f"{VERSION} {status_code} {phrase}", _clean_headers(headers))


def parse(raw: bytes) -> Message:
    """Parse exactly one TICKETPASS message (terminated by an empty line)."""
    try:
        text = raw.decode("utf-8").replace("\r\n", "\n")
    except UnicodeDecodeError as exc:
        raise ValueError("Message must be UTF-8") from exc

    lines = text.rstrip("\n").split("\n")
    if not lines or not lines[0].startswith(VERSION + " "):
        raise ValueError(f"Start line must begin with {VERSION}")

    headers: dict[str, str] = {}
    for line in lines[1:]:
        if not line:
            continue
        if ":" not in line:
            raise ValueError("Each header must contain ':'")
        key, value = line.split(":", 1)
        key, value = key.strip(), value.strip()
        if not key or not value or key in headers:
            raise ValueError("Invalid or duplicate header")
        headers[key] = value
    return Message(lines[0], headers)


def receive_message(sock, max_size: int = 8192) -> bytes:
    """Receive one empty-line-terminated message from a connected socket."""
    data = bytearray()
    while b"\r\n\r\n" not in data:
        chunk = sock.recv(1024)
        if not chunk:
            raise ConnectionError("Peer disconnected")
        data.extend(chunk)
        if len(data) > max_size:
            raise ValueError("Message exceeds maximum size")
    return bytes(data)


def _clean_headers(headers: dict[str, object]) -> dict[str, str]:
    return {key.replace("_", "-"): str(value) for key, value in headers.items() if value is not None}
