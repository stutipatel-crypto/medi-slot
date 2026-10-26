"""
config.py — Application configuration for Medi Slot.

All sensitive values (SECRET_KEY) should be set via environment variables
in production. See .env.example for reference.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).parent


class Config:
    # -----------------------------------------------------------------
    # Security
    # Never commit a real secret key.  Set SECRET_KEY in your environment
    # before deploying to production.
    # -----------------------------------------------------------------
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-insecure-key-change-in-production")

    # -----------------------------------------------------------------
    # Session
    # -----------------------------------------------------------------
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    # Set to True when serving over HTTPS in production
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true"
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour

    # -----------------------------------------------------------------
    # Data files
    # These files store JSON arrays.  They are NEVER reset on restart.
    # -----------------------------------------------------------------
    DOCTORS_FILE = BASE_DIR / "doctors.txt"
    USERS_FILE = BASE_DIR / "users.txt"
    APPOINTMENTS_FILE = BASE_DIR / "appointments.txt"
    NOTIFICATIONS_FILE = BASE_DIR / "notifications.txt"

    # -----------------------------------------------------------------
    # Booking mode
    # "demo"  — simulated booking; clearly labelled as a demonstration.
    # "live"  — requires confirmed clinic authorisation (not enabled).
    # -----------------------------------------------------------------
    BOOKING_MODE = os.environ.get("BOOKING_MODE", "demo")

    # -----------------------------------------------------------------
    # Queue (demo only)
    # -----------------------------------------------------------------
    QUEUE_MODE = os.environ.get("QUEUE_MODE", "demo")
    QUEUE_NOTIFICATION_THRESHOLD = int(os.environ.get("QUEUE_NOTIFICATION_THRESHOLD", "4"))
    DEFAULT_APPOINTMENT_DURATION_MINUTES = int(
        os.environ.get("DEFAULT_APPOINTMENT_DURATION_MINUTES", "15")
    )
    # Simulated patients already booked ahead of any new demo booking
    DEMO_PATIENTS_AHEAD_DEFAULT = int(os.environ.get("DEMO_PATIENTS_AHEAD_DEFAULT", "3"))

    # -----------------------------------------------------------------
    # Debug — disable in production
    # -----------------------------------------------------------------
    DEBUG = os.environ.get("FLASK_DEBUG", "true").lower() == "true"

    # -----------------------------------------------------------------
    # WTF / CSRF
    # -----------------------------------------------------------------
    WTF_CSRF_ENABLED = True
