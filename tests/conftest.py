"""
tests/conftest.py — Shared pytest fixtures for Medi Slot tests.

All tests use ISOLATED temporary files.
The real doctors.txt / users.txt / appointments.txt are NEVER touched.
"""

import json
import os
import tempfile
from pathlib import Path

import pytest

# The single real doctor record used across all tests
DOCTOR_RECORD = {
    "id": 1,
    "doctor_name": "Dr. Sanjiv Singh Rawat",
    "specialization": "Pediatrician",
    "qualifications": [
        "MBBS, Mahatma Gandhi Memorial Medical College, Indore, 1985",
        "MD - Pediatrics, Mahatma Gandhi Memorial Medical College, Indore, 1989",
    ],
    "clinic_name": "Child Care Hospital",
    "area": "Tilak Nagar",
    "city": "Indore",
    "state": "Madhya Pradesh",
    "country": "India",
    "address": "E-103, 104 Bakhtawar Ram Nagar, Indore, Indore",
    "consultation_fee": 600,
    "visiting_hours": {
        "Monday":    "09:00 AM - 05:00 PM",
        "Tuesday":   "09:00 AM - 05:00 PM",
        "Wednesday": "09:00 AM - 05:00 PM",
        "Thursday":  "09:00 AM - 05:00 PM",
        "Friday":    "09:00 AM - 05:00 PM",
        "Saturday":  "09:00 AM - 03:00 PM",
        "Sunday":    None,
    },
    "languages": ["English", "Hindi"],
    "professional_memberships": [
        "Indian Academy of Paediatrics (IAP)",
        "National Neonatology Forum (NNF)",
        "IAP Respiratory Chapter",
    ],
    "services_mentioned": [
        "Pediatric Vaccinations",
        "Pediatric Asthma Management",
        "Pediatric Consultation",
    ],
    "profile_image": "https://imagesx.practo.com/providers/dr-sanjiv-singh-rawat-pediatrician-ffc86b4e-40dc-4e75-ba0c-f711abf2471d.jpg?i_type=t_70x70",
    "data_source": "Information supplied by the project owner",
    "verification_status": "Needs verification",
    "clinic_booking_authorized": False,
    "video_consultation_available": None,
}


def _write_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")


@pytest.fixture()
def tmp_files():
    """Provide temporary JSON data files for each test."""
    with tempfile.TemporaryDirectory() as tmpdir:
        doctors_f      = os.path.join(tmpdir, "doctors.txt")
        users_f        = os.path.join(tmpdir, "users.txt")
        appointments_f = os.path.join(tmpdir, "appointments.txt")
        notifications_f = os.path.join(tmpdir, "notifications.txt")

        _write_json(doctors_f, [DOCTOR_RECORD])
        _write_json(users_f, [])
        _write_json(appointments_f, [])
        _write_json(notifications_f, [])

        yield {
            "doctors":       doctors_f,
            "users":         users_f,
            "appointments":  appointments_f,
            "notifications": notifications_f,
            "dir":           tmpdir,
        }


@pytest.fixture()
def app(tmp_files):
    """Flask test app using isolated temporary data files."""
    import app as flask_app_module

    flask_app_module.app.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False,
        SECRET_KEY="test-secret",
        DOCTORS_FILE=tmp_files["doctors"],
        USERS_FILE=tmp_files["users"],
        APPOINTMENTS_FILE=tmp_files["appointments"],
        NOTIFICATIONS_FILE=tmp_files["notifications"],
        BOOKING_MODE="demo",
        QUEUE_MODE="demo",
        DEMO_PATIENTS_AHEAD_DEFAULT=3,
    )
    yield flask_app_module.app


@pytest.fixture()
def client(app):
    """Flask test client."""
    return app.test_client()


@pytest.fixture()
def registered_user(client, tmp_files):
    """Register and return a test user (logged out)."""
    client.post("/signup", data={
        "name": "Test User",
        "email": "testuser@example.com",
        "password": "password123",
        "confirm_password": "password123",
    }, follow_redirects=True)
    return {"email": "testuser@example.com", "password": "password123", "name": "Test User"}


@pytest.fixture()
def logged_in_client(client, registered_user):
    """Flask test client with a logged-in user."""
    client.post("/login", data={
        "email": registered_user["email"],
        "password": registered_user["password"],
    }, follow_redirects=True)
    return client
