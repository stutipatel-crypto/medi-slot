"""
tests/test_appointments.py — Booking, cancellation, and rescheduling tests.
"""

import json
from datetime import date, timedelta
from pathlib import Path

import pytest

from services import appointment_service as appt_svc
from services import storage


def _tomorrow():
    return (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")


def _future(days=7):
    return (date.today() + timedelta(days=days)).strftime("%Y-%m-%d")


def _yesterday():
    return (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# Test 15: Past dates are rejected
# ---------------------------------------------------------------------------

def test_past_date_rejected(tmp_files):
    """Test 15: Past dates are rejected."""
    with pytest.raises(ValueError, match="past"):
        appt_svc.create_appointment(
            user_id=1,
            doctor_id=1,
            appointment_date=_yesterday(),
            appointment_time="10:00",
            filepath=tmp_files["appointments"],
        )


# ---------------------------------------------------------------------------
# Test 16: Invalid time slots are rejected
# ---------------------------------------------------------------------------

def test_outside_hours_rejected(tmp_files):
    """Test 16: Slots outside visiting hours are rejected."""
    # Monday, but at 6 AM (before 9 AM opening)
    # Find next Monday
    d = date.today() + timedelta(days=1)
    while d.strftime("%A") != "Monday":
        d += timedelta(days=1)
    with pytest.raises(ValueError, match="visiting hours"):
        appt_svc.create_appointment(
            user_id=1,
            doctor_id=1,
            appointment_date=d.strftime("%Y-%m-%d"),
            appointment_time="06:00",
            filepath=tmp_files["appointments"],
        )


def test_sunday_slot_rejected(tmp_files):
    """Sundays have no slots."""
    d = date.today() + timedelta(days=1)
    while d.strftime("%A") != "Sunday":
        d += timedelta(days=1)
    with pytest.raises(ValueError):
        appt_svc.create_appointment(
            user_id=1,
            doctor_id=1,
            appointment_date=d.strftime("%Y-%m-%d"),
            appointment_time="10:00",
            filepath=tmp_files["appointments"],
        )


# ---------------------------------------------------------------------------
# Test 17: Duplicate single-capacity slot bookings are prevented
# ---------------------------------------------------------------------------

def test_duplicate_slot_prevented(tmp_files):
    """Test 17: Two bookings for the same slot are rejected."""
    d = date.today() + timedelta(days=2)
    while d.strftime("%A") == "Sunday":
        d += timedelta(days=1)
    date_str = d.strftime("%Y-%m-%d")

    appt_svc.create_appointment(
        user_id=1,
        doctor_id=1,
        appointment_date=date_str,
        appointment_time="09:00",
        filepath=tmp_files["appointments"],
    )
    with pytest.raises(ValueError, match="already booked"):
        appt_svc.create_appointment(
            user_id=2,
            doctor_id=1,
            appointment_date=date_str,
            appointment_time="09:00",
            filepath=tmp_files["appointments"],
        )


# ---------------------------------------------------------------------------
# Test 18: Valid demo bookings persist
# ---------------------------------------------------------------------------

def test_valid_booking_persists(tmp_files):
    """Test 18: A valid demo booking is persisted to the appointments file."""
    d = date.today() + timedelta(days=3)
    while d.strftime("%A") == "Sunday":
        d += timedelta(days=1)
    date_str = d.strftime("%Y-%m-%d")

    appt = appt_svc.create_appointment(
        user_id=1,
        doctor_id=1,
        appointment_date=date_str,
        appointment_time="09:00",
        booking_mode="demo",
        filepath=tmp_files["appointments"],
    )

    assert appt["appointment_id"].startswith("MS-")
    assert appt["doctor_name"] == "Dr. Sanjiv Singh Rawat"
    assert appt["status"] == "pending_demo"

    # Verify it is actually written to the file
    data = json.loads(Path(tmp_files["appointments"]).read_text())
    assert any(a["appointment_id"] == appt["appointment_id"] for a in data)


# ---------------------------------------------------------------------------
# Test 14: Users cannot access other users' appointments
# ---------------------------------------------------------------------------

def test_user_cannot_access_others_appointment(logged_in_client, tmp_files, app):
    """Test 14: User A cannot view User B's appointment."""
    # Create another user's appointment directly in the file
    d = date.today() + timedelta(days=4)
    while d.strftime("%A") == "Sunday":
        d += timedelta(days=1)

    other_appt = {
        "appointment_id": "MS-AAAAAAAA",
        "user_id": 9999,  # Different user
        "doctor_id": 1,
        "doctor_name": "Dr. Sanjiv Singh Rawat",
        "clinic_name": "Child Care Hospital",
        "appointment_date": d.strftime("%Y-%m-%d"),
        "appointment_time": "10:00",
        "consultation_type": "In-person",
        "status": "pending_demo",
        "booking_mode": "demo",
        "created_at": "2026-01-01T10:00:00",
        "updated_at": "2026-01-01T10:00:00",
        "cancelled_at": None,
        "cancellation_reason": None,
    }
    data = json.loads(Path(tmp_files["appointments"]).read_text())
    data.append(other_appt)
    Path(tmp_files["appointments"]).write_text(json.dumps(data))

    with app.test_request_context():
        resp = logged_in_client.get("/appointment/MS-AAAAAAAA")
        assert resp.status_code in (403, 302)


# ---------------------------------------------------------------------------
# Test 19: Cancellation updates appointment status
# ---------------------------------------------------------------------------

def test_cancellation_updates_status(tmp_files):
    """Test 19: Cancellation changes status to 'cancelled', does not delete."""
    d = date.today() + timedelta(days=5)
    while d.strftime("%A") == "Sunday":
        d += timedelta(days=1)

    appt = appt_svc.create_appointment(
        user_id=1,
        doctor_id=1,
        appointment_date=d.strftime("%Y-%m-%d"),
        appointment_time="09:00",
        filepath=tmp_files["appointments"],
    )
    appt_id = appt["appointment_id"]

    cancelled = appt_svc.cancel_appointment(appt_id, user_id=1, filepath=tmp_files["appointments"])
    assert cancelled["status"] == "cancelled"
    assert cancelled["cancelled_at"] is not None

    # Record still exists (historical preservation)
    data = json.loads(Path(tmp_files["appointments"]).read_text())
    assert any(a["appointment_id"] == appt_id and a["status"] == "cancelled" for a in data)


def test_cancellation_wrong_user_raises(tmp_files):
    """Cancelling another user's appointment raises PermissionError."""
    d = date.today() + timedelta(days=5)
    while d.strftime("%A") == "Sunday":
        d += timedelta(days=1)

    appt = appt_svc.create_appointment(
        user_id=1,
        doctor_id=1,
        appointment_date=d.strftime("%Y-%m-%d"),
        appointment_time="11:00",
        filepath=tmp_files["appointments"],
    )
    with pytest.raises(PermissionError):
        appt_svc.cancel_appointment(appt["appointment_id"], user_id=999,
                                    filepath=tmp_files["appointments"])


# ---------------------------------------------------------------------------
# Test 20: Rescheduling checks slot availability
# ---------------------------------------------------------------------------

def test_reschedule_to_occupied_slot_rejected(tmp_files):
    """Test 20: Rescheduling to an already-booked slot is rejected."""
    d = date.today() + timedelta(days=6)
    while d.strftime("%A") == "Sunday":
        d += timedelta(days=1)
    date_str = d.strftime("%Y-%m-%d")

    appt1 = appt_svc.create_appointment(
        user_id=1, doctor_id=1,
        appointment_date=date_str, appointment_time="09:00",
        filepath=tmp_files["appointments"],
    )
    appt2 = appt_svc.create_appointment(
        user_id=2, doctor_id=1,
        appointment_date=date_str, appointment_time="09:15",
        filepath=tmp_files["appointments"],
    )

    with pytest.raises(ValueError, match="already booked"):
        appt_svc.reschedule_appointment(
            appt2["appointment_id"], user_id=2,
            new_date=date_str, new_time="09:00",
            filepath=tmp_files["appointments"],
        )


def test_reschedule_valid(tmp_files):
    """Valid reschedule updates the appointment."""
    d = date.today() + timedelta(days=8)
    while d.strftime("%A") == "Sunday":
        d += timedelta(days=1)
    date_str = d.strftime("%Y-%m-%d")
    new_d = date.today() + timedelta(days=9)
    while new_d.strftime("%A") == "Sunday":
        new_d += timedelta(days=1)
    new_date_str = new_d.strftime("%Y-%m-%d")

    appt = appt_svc.create_appointment(
        user_id=1, doctor_id=1,
        appointment_date=date_str, appointment_time="09:00",
        filepath=tmp_files["appointments"],
    )
    updated = appt_svc.reschedule_appointment(
        appt["appointment_id"], user_id=1,
        new_date=new_date_str, new_time="09:00",
        filepath=tmp_files["appointments"],
    )
    assert updated["appointment_date"] == new_date_str
    assert updated["status"] == "rescheduled_demo"
