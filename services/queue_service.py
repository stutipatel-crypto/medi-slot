"""
services/queue_service.py — Demo queue logic for Medi Slot.

IMPORTANT:
  All queue information is SIMULATED for demonstration purposes.
  This module has NO connection to any real clinic queue system.
  All displayed values must be clearly labelled as DEMO DATA.

Note: We do NOT estimate consultation duration because every doctor is different.
      Instead we show a suggested time to leave for the clinic
      (appointment time minus a fixed travel buffer of 15 minutes).
"""

from datetime import datetime, timedelta
from pathlib import Path

from services import storage

_DEFAULT_APPTS_FILE = Path(__file__).parent.parent / "appointments.txt"

# How many minutes before the appointment slot the patient should leave home.
TRAVEL_BUFFER_MINUTES = 15


def _file(filepath=None):
    return filepath or _DEFAULT_APPTS_FILE


def get_queue_position(appointment_id: str, filepath=None) -> dict:
    """
    Return a demo queue snapshot for the given appointment.

    The returned dict always contains:
      is_demo              -- True (always, for this implementation)
      queue_number         -- simulated queue number
      patients_ahead       -- simulated count (no wait-time estimate; doctors vary)
      suggested_leave_time -- human-readable time to leave for the clinic
      last_updated         -- ISO timestamp
    """
    appts = storage.read_json(_file(filepath))

    # Find the appointment
    target = None
    for a in appts:
        if a.get("appointment_id") == appointment_id:
            target = a
            break

    if target is None:
        return {"is_demo": True, "error": "Appointment not found"}

    if target.get("status") == "cancelled":
        return {
            "is_demo": True,
            "appointment_id": appointment_id,
            "queue_number": None,
            "patients_ahead": None,
            "suggested_leave_time": None,
            "status": "cancelled",
            "last_updated": datetime.now().isoformat(timespec="seconds"),
        }

    # Count same-day appointments for the same doctor that are earlier in the day
    appt_date = target.get("appointment_date", "")
    appt_time = target.get("appointment_time", "99:99")

    same_day = [
        a for a in appts
        if a.get("appointment_date") == appt_date
        and a.get("doctor_id") == target.get("doctor_id")
        and a.get("status") not in ("cancelled",)
        and a.get("appointment_time", "") < appt_time
    ]
    patients_ahead = len(same_day)

    # Queue number = position among all non-cancelled same-day slots sorted by time
    all_same_day_sorted = sorted(
        [a for a in appts
         if a.get("appointment_date") == appt_date
         and a.get("doctor_id") == target.get("doctor_id")
         and a.get("status") not in ("cancelled",)],
        key=lambda x: x.get("appointment_time", ""),
    )
    queue_number = next(
        (i + 1 for i, a in enumerate(all_same_day_sorted)
         if a.get("appointment_id") == appointment_id),
        None,
    )

    # Suggested leave time = appointment time minus TRAVEL_BUFFER_MINUTES.
    # We intentionally do NOT estimate consultation duration because every
    # doctor has a different consultation time.
    suggested_leave_time = None
    try:
        appt_dt = datetime.strptime(f"{appt_date} {appt_time}", "%Y-%m-%d %H:%M")
        leave_dt = appt_dt - timedelta(minutes=TRAVEL_BUFFER_MINUTES)
        suggested_leave_time = leave_dt.strftime("%I:%M %p")  # e.g. "08:45 AM"
    except ValueError:
        pass

    return {
        "is_demo": True,
        "appointment_id": appointment_id,
        "queue_number": queue_number,
        "patients_ahead": patients_ahead,
        "suggested_leave_time": suggested_leave_time,
        "status": target.get("status"),
        "last_updated": datetime.now().isoformat(timespec="seconds"),
    }


def should_warn_before_booking(patients_ahead: int, threshold: int = 10) -> bool:
    """
    Return True if the simulated queue is long enough to warn the user
    before they proceed with booking.
    """
    return patients_ahead >= threshold
