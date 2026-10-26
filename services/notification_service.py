"""
services/notification_service.py — In-app notification management.

Notifications are stored in notifications.txt as a JSON array.

Supported notification types:
  booking_confirmed   — A demo booking was created.
  booking_cancelled   — An appointment was cancelled.
  booking_rescheduled — An appointment was rescheduled.
  queue_threshold     — Patients-ahead crossed the configured threshold.

IMPORTANT:
  This service does NOT send SMS, email, WhatsApp, or push notifications.
  Only in-app notifications stored in notifications.txt are generated.
  Do not store sensitive medical information in notification messages.
"""

import uuid
from datetime import datetime
from pathlib import Path

from services import storage

_DEFAULT_FILE = Path(__file__).parent.parent / "notifications.txt"


def _file(filepath=None):
    return filepath or _DEFAULT_FILE


def _make_id() -> str:
    return "NTF-" + uuid.uuid4().hex[:8].upper()


def create_notification(
    user_id: int,
    notification_type: str,
    message: str,
    appointment_id: str = "",
    filepath=None,
) -> dict:
    """Create and persist a new notification for *user_id*."""
    record = {
        "notification_id": _make_id(),
        "user_id": user_id,
        "type": notification_type,
        "message": message,
        "appointment_id": appointment_id,
        "is_read": False,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    storage.append_record(_file(filepath), record)
    return record


def get_user_notifications(user_id: int, filepath=None) -> list:
    """Return all notifications for *user_id*, newest first."""
    all_notifs = storage.read_json(_file(filepath))
    user_notifs = [n for n in all_notifs if n.get("user_id") == user_id]
    return sorted(user_notifs, key=lambda n: n.get("created_at", ""), reverse=True)


def get_unread_count(user_id: int, filepath=None) -> int:
    """Return the number of unread notifications for *user_id*."""
    return sum(
        1 for n in storage.read_json(_file(filepath))
        if n.get("user_id") == user_id and not n.get("is_read", False)
    )


def mark_all_read(user_id: int, filepath=None) -> None:
    """Mark all notifications for *user_id* as read."""
    data = storage.read_json(_file(filepath))
    changed = False
    for i, n in enumerate(data):
        if n.get("user_id") == user_id and not n.get("is_read", False):
            data[i] = {**n, "is_read": True}
            changed = True
    if changed:
        storage.write_json(_file(filepath), data)


def has_threshold_notification(appointment_id: str, filepath=None) -> bool:
    """Return True if a queue_threshold notification already exists for this appointment."""
    return any(
        n.get("appointment_id") == appointment_id and n.get("type") == "queue_threshold"
        for n in storage.read_json(_file(filepath))
    )


# ---------------------------------------------------------------------------
# Convenience helpers called by routes
# ---------------------------------------------------------------------------

def notify_booking_confirmed(user_id: int, appointment_id: str, appt_date: str, appt_time: str, filepath=None):
    create_notification(
        user_id=user_id,
        notification_type="booking_confirmed",
        message=(
            f"Your demo appointment (ID: {appointment_id}) has been booked for "
            f"{appt_date} at {appt_time}. "
            "This is a DEMO booking — not a confirmed clinic appointment."
        ),
        appointment_id=appointment_id,
        filepath=filepath,
    )


def notify_booking_cancelled(user_id: int, appointment_id: str, filepath=None):
    create_notification(
        user_id=user_id,
        notification_type="booking_cancelled",
        message=f"Your appointment (ID: {appointment_id}) has been cancelled.",
        appointment_id=appointment_id,
        filepath=filepath,
    )


def notify_booking_rescheduled(user_id: int, appointment_id: str, new_date: str, new_time: str, filepath=None):
    create_notification(
        user_id=user_id,
        notification_type="booking_rescheduled",
        message=(
            f"Your appointment (ID: {appointment_id}) has been rescheduled to "
            f"{new_date} at {new_time}."
        ),
        appointment_id=appointment_id,
        filepath=filepath,
    )


def notify_queue_threshold(user_id: int, appointment_id: str, patients_ahead: int, filepath=None):
    if has_threshold_notification(appointment_id, filepath=filepath):
        return  # Prevent duplicate notifications
    create_notification(
        user_id=user_id,
        notification_type="queue_threshold",
        message=(
            f"Queue update for appointment {appointment_id}: "
            f"{patients_ahead} patients are ahead of you (DEMO DATA)."
        ),
        appointment_id=appointment_id,
        filepath=filepath,
    )
