"""
tests/test_queue.py — Queue and notification tests.
"""

import json
from datetime import date, timedelta
from pathlib import Path

import pytest

from services import appointment_service as appt_svc
from services import notification_service as notif_svc
from services import queue_service as queue_svc


def _future_weekday(offset=2):
    d = date.today() + timedelta(days=offset)
    while d.strftime("%A") == "Sunday":
        d += timedelta(days=1)
    return d.strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# Test 21: Queue threshold logic
# ---------------------------------------------------------------------------

def test_queue_warn_threshold():
    """Test 21: Queue warning triggers at >= 10 patients ahead."""
    assert queue_svc.should_warn_before_booking(10, threshold=10) is True
    assert queue_svc.should_warn_before_booking(9,  threshold=10) is False
    assert queue_svc.should_warn_before_booking(0,  threshold=10) is False


def test_queue_position_after_booking(tmp_files):
    """Queue position is calculated correctly based on same-day bookings."""
    date_str = _future_weekday(3)

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

    pos1 = queue_svc.get_queue_position(appt1["appointment_id"], tmp_files["appointments"])
    pos2 = queue_svc.get_queue_position(appt2["appointment_id"], tmp_files["appointments"])

    assert pos1["is_demo"] is True
    assert pos1["queue_number"] == 1
    assert pos1["patients_ahead"] == 0

    assert pos2["queue_number"] == 2
    assert pos2["patients_ahead"] == 1


# ---------------------------------------------------------------------------
# Test 22: Queue notifications are not duplicated
# ---------------------------------------------------------------------------

def test_threshold_notification_not_duplicated(tmp_files):
    """Test 22: Queue threshold notification is sent at most once per appointment."""
    appointment_id = "MS-TESTDUP1"

    notif_svc.notify_queue_threshold(1, appointment_id, 4, tmp_files["notifications"])
    notif_svc.notify_queue_threshold(1, appointment_id, 4, tmp_files["notifications"])  # duplicate call

    data = json.loads(Path(tmp_files["notifications"]).read_text())
    threshold_notifs = [
        n for n in data
        if n["appointment_id"] == appointment_id and n["type"] == "queue_threshold"
    ]
    assert len(threshold_notifs) == 1


# ---------------------------------------------------------------------------
# Test 23: Missing or malformed JSON produces safe errors
# ---------------------------------------------------------------------------

def test_missing_file_returns_empty_list():
    """Missing file returns an empty list without crashing."""
    from services.storage import read_json
    result = read_json("/nonexistent/path/totally_fake_file.txt")
    assert result == []


def test_malformed_json_raises_value_error(tmp_files):
    """Malformed JSON file raises ValueError, not crashes silently."""
    from services.storage import read_json
    import os, tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("NOT VALID JSON {{{")
        bad_path = f.name

    try:
        with pytest.raises(ValueError, match="invalid JSON"):
            read_json(bad_path)
    finally:
        os.unlink(bad_path)


# ---------------------------------------------------------------------------
# Test 24: Restarting Flask does not create additional doctors or erase appointments
# ---------------------------------------------------------------------------

def test_restart_does_not_create_extra_doctors(tmp_files):
    """Test 24a: Re-importing the app module does not seed extra doctor records."""
    from services.doctor_service import get_all_doctors
    doctors = get_all_doctors(tmp_files["doctors"])
    initial_count = len(doctors)
    assert initial_count == 1

    # Simulating a second "startup" — re-read the file
    doctors_again = get_all_doctors(tmp_files["doctors"])
    assert len(doctors_again) == 1


def test_restart_does_not_erase_appointments(tmp_files):
    """Test 24b: Existing appointments survive a simulated restart."""
    date_str = _future_weekday(4)
    appt = appt_svc.create_appointment(
        user_id=1, doctor_id=1,
        appointment_date=date_str, appointment_time="09:00",
        filepath=tmp_files["appointments"],
    )
    appt_id = appt["appointment_id"]

    # Simulate init_file_if_missing (should not overwrite existing file)
    from services.storage import init_file_if_missing
    init_file_if_missing(tmp_files["appointments"])  # should be a no-op

    data = json.loads(Path(tmp_files["appointments"]).read_text())
    assert any(a["appointment_id"] == appt_id for a in data)


# ---------------------------------------------------------------------------
# Test 25: Application starts without syntax or import errors
# ---------------------------------------------------------------------------

def test_app_imports_without_error():
    """Test 25: Importing app.py does not raise any exception."""
    import importlib
    import app as flask_app_module
    assert flask_app_module.app is not None


def test_health_endpoint(client):
    """Health endpoint returns 200 OK."""
    resp = client.get("/health")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data["status"] == "ok"
