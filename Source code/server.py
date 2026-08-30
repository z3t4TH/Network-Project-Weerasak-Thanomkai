"""Concurrent TCP server implementing TICKETPASS/1.0."""

import socket
from threading import Thread

from protocol import parse, receive_message, response
from reservation_manager import ReservationError, ReservationManager

HOST, PORT = "127.0.0.1", 5050
manager = ReservationManager()


def required(headers: dict[str, str], *names: str) -> list[str]:
    missing = [name for name in names if name not in headers]
    if missing:
        raise ReservationError(400, "BAD_REQUEST", f"Missing header(s): {', '.join(missing)}")
    return [headers[name] for name in names]


def handle(message):
    parts = message.start_line.split()
    if len(parts) != 2:
        raise ReservationError(400, "BAD_REQUEST", "Invalid request start line")
    command, headers = parts[1], message.headers

    if command == "CHECK":
        code, phrase, data = 200, "OK", manager.check(headers.get("Zone"))
    elif command == "HOLD":
        request_id, user_id, zone, quantity, seconds = required(headers, "Request-ID", "User-ID", "Zone", "Quantity", "Hold-Seconds")
        code, phrase, data = manager.hold(request_id, user_id, zone, int(quantity), int(seconds))
    elif command == "CONFIRM":
        reservation_id, = required(headers, "Reservation-ID")
        code, phrase, data = manager.confirm(reservation_id)
    elif command == "CANCEL":
        reservation_id, = required(headers, "Reservation-ID")
        code, phrase, data = manager.cancel(reservation_id)
    elif command == "STATUS":
        reservation_id, = required(headers, "Reservation-ID")
        code, phrase, data = manager.status(reservation_id)
    else:
        raise ReservationError(400, "BAD_REQUEST", f"Unknown command: {command}")
    return response(code, phrase, **data)


def client_session(conn: socket.socket, address):
    with conn:
        try:
            raw = receive_message(conn)
            print(f"\n[RECEIVED from {address}]\n{raw.decode().strip()}")
            try:
                reply = handle(parse(raw))
            except ReservationError as exc:
                reply = response(exc.code, exc.phrase, Detail=exc.detail)
            except (ValueError, TypeError) as exc:
                reply = response(400, "BAD_REQUEST", Detail=str(exc))
            conn.sendall(reply.to_bytes())
            print(f"[SENT]\n{reply.to_bytes().decode().strip()}")
        except (ConnectionError, OSError, ValueError) as exc:
            print(f"Connection {address} closed: {exc}")


def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, PORT))
        server.listen()
        print(f"TICKETPASS server listening on {HOST}:{PORT}")
        while True:
            conn, address = server.accept()
            Thread(target=client_session, args=(conn, address), daemon=True).start()


if __name__ == "__main__":
    main()
