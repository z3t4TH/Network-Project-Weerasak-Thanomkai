"""Interactive console client for TICKETPASS/1.0."""

import socket
from uuid import uuid4

from protocol import parse, receive_message, request

HOST, PORT = "127.0.0.1", 5050


def send(message):
    print(f"\n[SENT]\n{message.to_bytes().decode().strip()}")
    with socket.create_connection((HOST, PORT)) as sock:
        sock.sendall(message.to_bytes())
        raw = receive_message(sock)
    print(f"[RECEIVED]\n{raw.decode().strip()}")
    return parse(raw)


def main():
    print("TICKETPASS/1.0 Client")
    print("Commands: check, hold, confirm, cancel, status, quit")
    while True:
        command = input("\nTICKETPASS> ").strip().lower()
        if command == "quit":
            return
        if command == "check":
            zone = input("Zone (VIP/A/B, blank = all): ").strip().upper()
            send(request("CHECK", Zone=zone or None))
        elif command == "hold":
            zone = input("Zone: ").strip().upper()
            quantity = input("Quantity: ").strip()
            user_id = input("User ID: ").strip()
            reply = send(request("HOLD", **{
                "Request-ID": f"REQ-{uuid4().hex[:8].upper()}", "User-ID": user_id,
                "Zone": zone, "Quantity": quantity, "Hold-Seconds": 60,
            }))
            if "Reservation-ID" in reply.headers:
                print("Save this ID for confirm/status:", reply.headers["Reservation-ID"])
        elif command in {"confirm", "cancel", "status"}:
            reservation_id = input("Reservation ID: ").strip()
            send(request(command, **{"Reservation-ID": reservation_id}))
        else:
            print("Unknown command")


if __name__ == "__main__":
    main()
