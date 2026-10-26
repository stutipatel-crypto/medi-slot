"""
services/appointment_service.py — Appointment booking, retrieval,
cancellation, and rescheduling for Medi Slot.

All appointments are stored in appointments.txt as a JSON array.
The booking workflow is in DEMO MODE by default.  Live clinic booking
requires clinic authorisation (not yet enabled).
"""

import uuid
from datetime import datetime, date, time as dt_time
from pathlib import Path

from services import storage

_DEFAULT_FILE = Path(__file__).parent.parent / "appointments.txt"

# Slot duration in minutes (used to derive available slots from visiting hours)
DEFAULT_SLOT_MINUTES = 15

# Visiting hours that carry confirmed availability (demo only)
# Key: weekday name  Value: (start_time, end_time) as datetime.time objects
VISITING_HOURS = {
    "Monday":    (dt_time(9, 0),  dt_time(17, 0)),
    "Tuesday":   (dt_time(9, 0),  dt_time(17, 0)),
    "Wednesday": (dt_time(9, 0),  dt_time(17, 0)),
    "Thursday":  (dt_time(9, 0),  dt_time(17, 0)),
    "Friday":    (dt_time(9, 0),  dt_time(17, 0)),
    "Saturday":  (dt_time(9, 0),  dt_time(15, 0)),
    "Sunday":    None,
}


def _file(filepath=None):
    return filepath or _DEFAULT_FILE


def _generate_appointment_id() -> str:
    return "MS-" + uuid.uuid4().hex[:8].upper()


# ---------------------------------------------------------------------------
# Slot helpers
# ---------------------------------------------------------------------------

def get_available_slots(appt_date: date, slot_minutes: int = DEFAULT_SLOT_MINUTES, filepath=None) -> list[str]:
    """
    Return a list of HH:MM slot strings for *appt_date* that are not
    already booked in a confirmed/pending appointment.

    NOTE: These are demo slots derived from the configured visiting hours.
    They do NOT represent real-time clinic availability.
    """
    weekday = appt_date.strftime("%A")
    hours = VISITING_HOURS.get(weekday)
    if hours is None:
        return []  # Sunday or unknown — no slots

    start_t, end_t = hours
    slots = []
    current = datetime.combine(appt_date, start_t)
    end_dt = datetime.combine(appt_date, end_t)
    while current < end_dt:
        slots.append(current.strftime("%H:%M"))
        from datetime import timedelta
        current += timedelta(minutes=slot_minutes)

    # Remove already-booked slots
    booked = _booked_slots_on_date(appt_date, filepath=filepath)
    return [s for s in slots if s not in booked]


def _booked_slots_on_date(appt_date: date, exclude_id: str = "", filepath=None) -> set[str]:
    """Return the set of time strings already booked for a given date."""
    appointments = storage.read_json(_file(filepath))
    booked = set()
    date_str = appt_date.strftime("%Y-%m-%d")
    for a in appointments:
        if a.get("appointment_id") == exclude_id:
            continue
        if a.get("status") in ("cancelled",):
            continue
        if a.get("appointment_date") == date_str:
            booked.add(a.get("appointment_time", ""))
    return booked


def is_slot_available(appt_date: date, time_str: str, exclude_id: str = "", filepath=None) -> bool:
    """Return True if *time_str* (HH:MM) on *appt_date* is not yet booked."""
    booked = _booked_slots_on_date(appt_date, exclude_id=exclude_id, filepath=filepath)
    return time_str not in booked


def is_time_within_hours(appt_date: date, time_str: str) -> bool:
    """Return True if HH:MM falls within the doctor's visiting hours for that weekday."""
    weekday = appt_date.strftime("%A")
    hours = VISITING_HOURS.get(weekday)
    if not hours:
        return False
    try:
        h, m = map(int, time_str.split(":"))
        t = dt_time(h, m)
    except (ValueError, AttributeError):
        return False
    return hours[0] <= t < hours[1]


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

def create_appointment(
    *,
    user_id: int,
    doctor_id: int,
    appointment_date: str,   # "YYYY-MM-DD"
    appointment_time: str,   # "HH:MM"
    consultation_type: str = "In-person",
    booking_mode: str = "demo",
    filepath=None,
) -> dict:
    """
    Validate and create a new appointment record.
    Raises ValueError on invalid input or unavailable slot.
    """
    # --- Date validation ---
    try:
        appt_date = datetime.strptime(appointment_date, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError("Invalid date format.  Use YYYY-MM-DD.")
    if appt_date < date.today():
        raise ValueError("Appointment date cannot be in the past.")

    # --- Doctor must exist (id=1 only) ---
    if doctor_id != 1:
        raise ValueError("Invalid doctor ID.")

    # --- Time validation ---
    try:
        datetime.strptime(appointment_time, "%H:%M")
    except ValueError:
        raise ValueError("Invalid time format.  Use HH:MM.")
    if not is_time_within_hours(appt_date, appointment_time):
        raise ValueError(
            f"Selected time {appointment_time} is outside the doctor's visiting hours "
            f"for {appt_date.strftime('%A')}."
        )

    # --- One appointment per day per user ---
    existing = get_user_appointment_on_date(user_id, appt_date, filepath=filepath)
    if existing:
        raise ValueError(
            f"__ONE_PER_DAY__{existing['appointment_id']}__"
            f"You already have an appointment on {appointment_date} "
            f"at {existing['appointment_time']}. "
            "Please cancel it before booking a new one for the same day."
        )

    # --- Slot availability ---
    if not is_slot_available(appt_date, appointment_time, filepath=filepath):
        raise ValueError(
            f"The slot at {appointment_time} on {appointment_date} is already booked. "
            "Please choose a different time."
        )

    appointment_id = _generate_appointment_id()
    now = datetime.now().isoformat(timespec="seconds")

    record = {
        "appointment_id": appointment_id,
        "user_id": user_id,
        "doctor_id": doctor_id,
        "doctor_name": "Dr. Sanjiv Singh Rawat",
        "clinic_name": "Child Care Hospital",
        "appointment_date": appointment_date,
        "appointment_time": appointment_time,
        "consultation_type": consultation_type,
        "status": "pending_demo" if booking_mode == "demo" else "confirmed",
        "booking_mode": booking_mode,
        "created_at": now,
        "updated_at": now,
        "cancelled_at": None,
        "cancellation_reason": None,
        "_fee_note": "Consultation fee of Rs.600 requires confirmation before live booking.",
    }

    storage.append_record(_file(filepath), record)
    return record


def get_appointment(appointment_id: str, filepath=None) -> dict | None:
    """Return the appointment record by ID, or None."""
    for a in storage.read_json(_file(filepath)):
        if a.get("appointment_id") == appointment_id:
            return a
    return None


def get_user_appointment_on_date(user_id: int, appt_date: date, filepath=None) -> dict | None:
    """
    Return the first active (non-cancelled) appointment the user has on *appt_date*,
    or None if they have none.  Used to enforce one-appointment-per-day rule.
    """
    date_str = appt_date.strftime("%Y-%m-%d")
    for a in storage.read_json(_file(filepath)):
        if (
            a.get("user_id") == user_id
            and a.get("appointment_date") == date_str
            and a.get("status") not in ("cancelled",)
        ):
            return a
    return None


def get_user_appointments(user_id: int, filepath=None) -> list:
    """Return all appointments belonging to *user_id*, newest first."""
    appts = [a for a in storage.read_json(_file(filepath)) if a.get("user_id") == user_id]
    return sorted(appts, key=lambda a: a.get("created_at", ""), reverse=True)


def cancel_appointment(appointment_id: str, user_id: int, filepath=None) -> dict:
    """
    Cancel an appointment.  Raises ValueError on authorization or state errors.
    Returns the updated record.
    """
    appt = get_appointment(appointment_id, filepath=filepath)
    if not appt:
        raise ValueError("Appointment not found.")
    if appt.get("user_id") != user_id:
        raise PermissionError("You are not authorized to cancel this appointment.")
    if appt.get("status") == "cancelled":
        raise ValueError("This appointment is already cancelled.")

    now = datetime.now().isoformat(timespec="seconds")
    updates = {
        "status": "cancelled",
        "cancelled_at": now,
        "updated_at": now,
    }
    _update_appointment(appointment_id, updates, filepath=filepath)
    return {**appt, **updates}


def reschedule_appointment(
    appointment_id: str,
    user_id: int,
    new_date: str,
    new_time: str,
    filepath=None,
) -> dict:
    """
    Reschedule an appointment to a new date and time.
    Validates availability before releasing the old slot.
    Raises ValueError or PermissionError on failure.
    """
    appt = get_appointment(appointment_id, filepath=filepath)
    if not appt:
        raise ValueError("Appointment not found.")
    if appt.get("user_id") != user_id:
        raise PermissionError("You are not authorized to reschedule this appointment.")
    if appt.get("status") == "cancelled":
        raise ValueError("Cancelled appointments cannot be rescheduled.")

    # Validate new date
    try:
        new_appt_date = datetime.strptime(new_date, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError("Invalid date format.")
    if new_appt_date < date.today():
        raise ValueError("New date cannot be in the past.")

    # Validate new time
    try:
        datetime.strptime(new_time, "%H:%M")
    except ValueError:
        raise ValueError("Invalid time format.")
    if not is_time_within_hours(new_appt_date, new_time):
        raise ValueError(
            f"Selected time {new_time} is outside visiting hours for "
            f"{new_appt_date.strftime('%A')}."
        )

    # Check availability (exclude current appointment's slot)
    if not is_slot_available(new_appt_date, new_time, exclude_id=appointment_id, filepath=filepath):
        raise ValueError(
            f"The slot at {new_time} on {new_date} is already booked. "
            "Please choose a different time."
        )

    now = datetime.now().isoformat(timespec="seconds")
    updates = {
        "appointment_date": new_date,
        "appointment_time": new_time,
        "status": "rescheduled_demo",
        "updated_at": now,
        "previous_date": appt.get("appointment_date"),
        "previous_time": appt.get("appointment_time"),
    }
    _update_appointment(appointment_id, updates, filepath=filepath)
    return {**appt, **updates}


def _update_appointment(appointment_id: str, updates: dict, filepath=None) -> None:
    data = storage.read_json(_file(filepath))
    for i, a in enumerate(data):
        if a.get("appointment_id") == appointment_id:
            data[i] = {**a, **updates}
            storage.write_json(_file(filepath), data)
            return
