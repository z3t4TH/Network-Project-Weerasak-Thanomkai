"""Thread-safe reservation state for the TIXLOCK demonstration server."""

from datetime import UTC, datetime, timedelta
from threading import Lock
from uuid import uuid4


class ReservationError(Exception):
    def __init__(self, code: int, phrase: str, detail: str):
        self.code, self.phrase, self.detail = code, phrase, detail
        super().__init__(detail)


class ReservationManager:
    def __init__(self, inventory: dict[str, int] | None = None):
        self.inventory = inventory or {"VIP": 5, "A": 20, "B": 50}
        self.reservations: dict[str, dict] = {}
        self.request_results: dict[str, tuple[int, str, dict[str, str]]] = {}
        self.lock = Lock()

    def check(self, zone: str | None = None) -> dict[str, str]:
        with self.lock:
            self._expire_holds()
            if zone:
                self._require_zone(zone)
                return {"Zone": zone, "Available": str(self.inventory[zone])}
            return {f"Available-{key}": str(value) for key, value in self.inventory.items()}

    def hold(self, request_id: str, user_id: str, zone: str, quantity: int, hold_seconds: int):
        with self.lock:
            self._expire_holds()
            cached = self.request_results.get(request_id)
            if cached:
                return cached
            self._require_zone(zone)
            if quantity < 1 or hold_seconds < 1 or hold_seconds > 300:
                raise ReservationError(400, "BAD_REQUEST", "Quantity must be positive; Hold-Seconds must be 1..300")
            if self.inventory[zone] < quantity:
                raise ReservationError(409, "SOLD_OUT", "Not enough tickets available")

            reservation_id = f"RES-{uuid4().hex[:8].upper()}"
            expires_at = datetime.now(UTC) + timedelta(seconds=hold_seconds)
            self.inventory[zone] -= quantity
            self.reservations[reservation_id] = {
                "user_id": user_id, "zone": zone, "quantity": quantity,
                "state": "HELD", "expires_at": expires_at,
            }
            result = (201, "HELD", {
                "Request-ID": request_id, "Reservation-ID": reservation_id,
                "Zone": zone, "Quantity": str(quantity),
                "Expires-At": expires_at.isoformat(),
            })
            self.request_results[request_id] = result
            return result

    def confirm(self, reservation_id: str):
        with self.lock:
            self._expire_holds()
            booking = self._get(reservation_id)
            if booking["state"] == "BOOKED":
                return 200, "BOOKED", {"Reservation-ID": reservation_id, "Status": "Already confirmed"}
            if booking["state"] != "HELD":
                raise ReservationError(410, "HOLD_EXPIRED", "Reservation is no longer active")
            booking["state"] = "BOOKED"
            return 200, "BOOKED", {"Reservation-ID": reservation_id, "Zone": booking["zone"], "Quantity": str(booking["quantity"])}

    def cancel(self, reservation_id: str):
        with self.lock:
            self._expire_holds()
            booking = self._get(reservation_id)
            if booking["state"] == "HELD":
                self.inventory[booking["zone"]] += booking["quantity"]
                booking["state"] = "CANCELLED"
            return 200, "CANCELLED", {"Reservation-ID": reservation_id, "Status": booking["state"]}

    def status(self, reservation_id: str):
        with self.lock:
            self._expire_holds()
            booking = self._get(reservation_id)
            return 200, "OK", {
                "Reservation-ID": reservation_id, "Status": booking["state"],
                "Zone": booking["zone"], "Quantity": str(booking["quantity"]),
            }

    def _expire_holds(self):
        now = datetime.now(UTC)
        for booking in self.reservations.values():
            if booking["state"] == "HELD" and booking["expires_at"] <= now:
                booking["state"] = "EXPIRED"
                self.inventory[booking["zone"]] += booking["quantity"]

    def _get(self, reservation_id: str) -> dict:
        if reservation_id not in self.reservations:
            raise ReservationError(404, "NOT_FOUND", "Reservation-ID does not exist")
        return self.reservations[reservation_id]

    def _require_zone(self, zone: str):
        if zone not in self.inventory:
            raise ReservationError(404, "NOT_FOUND", "Zone does not exist")
