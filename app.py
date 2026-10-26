"""
app.py — Main Flask application for Medi Slot.

Start the server:
    py app.py

Visit: http://127.0.0.1:5000/

IMPORTANT: The active doctor directory contains EXACTLY ONE doctor:
Dr. Sanjiv Singh Rawat.  No other doctor will ever be shown.
"""

import logging
import os
from datetime import datetime, date
from functools import wraps
from pathlib import Path

from dotenv import load_dotenv
from flask import (
    Flask,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import (
    LoginManager,
    UserMixin,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import check_password_hash, generate_password_hash

from config import Config
from services import storage
from services import appointment_service as appt_svc
from services import doctor_service as doc_svc
from services import notification_service as notif_svc
from services import queue_service as queue_svc

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

load_dotenv()  # Load .env if it exists (development convenience)

app = Flask(__name__)
app.config.from_object(Config)

csrf = CSRFProtect(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message = "Please log in to access this page."
login_manager.login_message_category = "warning"

# Safe logging — never log passwords
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("medislot")

# ---------------------------------------------------------------------------
# Ensure data files exist (NEVER reset existing data)
# ---------------------------------------------------------------------------

for _f in [
    app.config["USERS_FILE"],
    app.config["APPOINTMENTS_FILE"],
    app.config["NOTIFICATIONS_FILE"],
]:
    storage.init_file_if_missing(_f)

# Verify doctors.txt has exactly one record (Dr. Sanjiv Singh Rawat)
_doctors = doc_svc.get_all_doctors(app.config["DOCTORS_FILE"])
if len(_doctors) != 1 or _doctors[0].get("id") != 1:
    logger.warning(
        "doctors.txt does not contain exactly one record (id=1). "
        "The application expects ONLY Dr. Sanjiv Singh Rawat (id=1)."
    )


# ---------------------------------------------------------------------------
# User model (Flask-Login)
# ---------------------------------------------------------------------------

class User(UserMixin):
    def __init__(self, data: dict):
        self._data = data

    @property
    def id(self):
        return str(self._data["id"])

    @property
    def user_id(self) -> int:
        return self._data["id"]

    @property
    def name(self) -> str:
        return self._data.get("name", "")

    @property
    def email(self) -> str:
        return self._data.get("email", "")

    @classmethod
    def from_id(cls, user_id: int):
        record = storage.find_by_id(app.config["USERS_FILE"], int(user_id))
        if record:
            return cls(record)
        return None


@login_manager.user_loader
def load_user(user_id):
    return User.from_id(int(user_id))


# ---------------------------------------------------------------------------
# Template context processor — inject common data into every template
# ---------------------------------------------------------------------------

@app.context_processor
def inject_globals():
    unread_count = 0
    if current_user.is_authenticated:
        try:
            unread_count = notif_svc.get_unread_count(
                current_user.user_id, app.config["NOTIFICATIONS_FILE"]
            )
        except Exception:
            pass
    return {
        "unread_notifications": unread_count,
        "current_year": datetime.now().year,
        "booking_mode": app.config.get("BOOKING_MODE", "demo"),
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_doctor_or_404(doctor_id: int):
    doc = doc_svc.get_doctor_by_id(doctor_id, app.config["DOCTORS_FILE"])
    if doc is None:
        abort(404)
    return doc


def _get_appointment_or_404(appointment_id: str):
    appt = appt_svc.get_appointment(appointment_id, app.config["APPOINTMENTS_FILE"])
    if appt is None:
        abort(404)
    return appt


def _require_own_appointment(appt: dict):
    if appt.get("user_id") != current_user.user_id:
        abort(403)


# ---------------------------------------------------------------------------
# Routes — Public
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    """Homepage with hero search form and featured doctor section."""
    doctor = doc_svc.get_doctor_by_id(1, app.config["DOCTORS_FILE"])
    return render_template("index.html", featured_doctor=doctor)


@app.route("/health")
def health():
    return jsonify({"status": "ok", "timestamp": datetime.now().isoformat()})


# ---------------------------------------------------------------------------
# Routes — Auth
# ---------------------------------------------------------------------------

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        errors = []
        if not name or len(name) < 2:
            errors.append("Full name must be at least 2 characters.")
        if not email or "@" not in email:
            errors.append("A valid email address is required.")
        if len(password) < 6:
            errors.append("Password must be at least 6 characters.")
        if password != confirm:
            errors.append("Passwords do not match.")

        if not errors:
            existing = storage.find_one_by_field(app.config["USERS_FILE"], "email", email)
            if existing:
                errors.append("An account with this email already exists.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("signup.html", name=name, email=email)

        new_id = storage.next_int_id(app.config["USERS_FILE"])
        hashed = generate_password_hash(password)
        user_record = {
            "id": new_id,
            "name": name,
            "email": email,
            "password_hash": hashed,
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        storage.append_record(app.config["USERS_FILE"], user_record)
        logger.info("New user registered: id=%s email=%s", new_id, email)

        user_obj = User(user_record)
        login_user(user_obj)
        flash(f"Welcome to Medi Slot, {name}! Your account has been created.", "success")
        return redirect(url_for("dashboard"))

    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        record = storage.find_one_by_field(app.config["USERS_FILE"], "email", email)
        if record and check_password_hash(record.get("password_hash", ""), password):
            user_obj = User(record)
            login_user(user_obj)
            logger.info("User logged in: id=%s", record["id"])
            next_page = request.args.get("next")
            if next_page and next_page.startswith("/"):
                return redirect(next_page)
            return redirect(url_for("dashboard"))

        flash("Invalid email or password. Please try again.", "danger")
        return render_template("login.html", email=email)

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logger.info("User logged out: id=%s", current_user.user_id)
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))


# ---------------------------------------------------------------------------
# Routes — Dashboard
# ---------------------------------------------------------------------------

@app.route("/dashboard")
@login_required
def dashboard():
    appts = appt_svc.get_user_appointments(
        current_user.user_id, app.config["APPOINTMENTS_FILE"]
    )
    today_str = date.today().strftime("%Y-%m-%d")
    upcoming = [a for a in appts if a.get("appointment_date", "") >= today_str
                and a.get("status") not in ("cancelled",)]
    recent = appts[:5]
    notifs = notif_svc.get_user_notifications(
        current_user.user_id, app.config["NOTIFICATIONS_FILE"]
    )[:5]
    return render_template(
        "dashboard.html",
        upcoming=upcoming,
        recent_appointments=recent,
        notifications=notifs,
    )


# ---------------------------------------------------------------------------
# Routes — Doctor search & profile
# ---------------------------------------------------------------------------

@app.route("/doctors")
def search_doctors():
    country = request.args.get("country", "").strip()
    state = request.args.get("state", "").strip()
    city = request.args.get("city", "").strip()
    area = request.args.get("area", "").strip()
    specialization = request.args.get("specialization", "").strip()
    medical_system = request.args.get("medical_system", "").strip()

    searched = any([country, state, city, area, specialization, medical_system])
    results = []
    if searched:
        results = doc_svc.search_doctors(
            country=country,
            state=state,
            city=city,
            area=area,
            specialization=specialization,
            medical_system=medical_system,
            filepath=app.config["DOCTORS_FILE"],
        )

    return render_template(
        "search_doctors.html",
        results=results,
        searched=searched,
        country=country,
        state=state,
        city=city,
        area=area,
        specialization=specialization,
        medical_system=medical_system,
    )


@app.route("/doctor/<int:doctor_id>")
def doctor_profile(doctor_id):
    doc = _get_doctor_or_404(doctor_id)
    return render_template("doctor_profile.html", doctor=doc)


# ---------------------------------------------------------------------------
# Routes — Booking
# ---------------------------------------------------------------------------

@app.route("/book/<int:doctor_id>", methods=["GET", "POST"])
@login_required
def book_appointment(doctor_id):
    doc = _get_doctor_or_404(doctor_id)
    booking_mode = app.config.get("BOOKING_MODE", "demo")

    if request.method == "POST":
        appt_date_str = request.form.get("appointment_date", "").strip()
        appt_time = request.form.get("appointment_time", "").strip()
        consultation_type = request.form.get("consultation_type", "In-person").strip()

        # Parse conflicting appointment id embedded in the ValueError message
        conflicting_appt = None
        try:
            appt = appt_svc.create_appointment(
                user_id=current_user.user_id,
                doctor_id=doctor_id,
                appointment_date=appt_date_str,
                appointment_time=appt_time,
                consultation_type=consultation_type,
                booking_mode=booking_mode,
                filepath=app.config["APPOINTMENTS_FILE"],
            )
            notif_svc.notify_booking_confirmed(
                current_user.user_id,
                appt["appointment_id"],
                appt_date_str,
                appt_time,
                app.config["NOTIFICATIONS_FILE"],
            )
            logger.info(
                "Appointment booked: id=%s user=%s",
                appt["appointment_id"], current_user.user_id,
            )
            return redirect(url_for("booking_confirmation", appointment_id=appt["appointment_id"]))
        except (ValueError, PermissionError) as exc:
            msg = str(exc)
            if msg.startswith("__ONE_PER_DAY__"):
                # Extract the conflicting appointment id from the sentinel
                parts = msg.split("__")
                conflict_id = parts[2] if len(parts) >= 3 else None
                conflicting_appt = appt_svc.get_appointment(
                    conflict_id, app.config["APPOINTMENTS_FILE"]
                ) if conflict_id else None
                # Show user-friendly message without the sentinel
                clean_msg = msg.split("__", 3)[-1] if "__" in msg else msg
                flash(clean_msg, "danger")
            else:
                flash(msg, "danger")

        # Re-render form with conflicting_appt highlighted
        from datetime import timedelta
        default_date = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
        selected_date_str = appt_date_str or default_date
        try:
            selected_date = datetime.strptime(selected_date_str, "%Y-%m-%d").date()
            if selected_date < date.today():
                selected_date = date.today() + timedelta(days=1)
        except ValueError:
            selected_date = date.today() + timedelta(days=1)

        available_slots = appt_svc.get_available_slots(
            selected_date, filepath=app.config["APPOINTMENTS_FILE"]
        )
        demo_patients_ahead = app.config.get("DEMO_PATIENTS_AHEAD_DEFAULT", 3)
        show_queue_warning = queue_svc.should_warn_before_booking(
            demo_patients_ahead, threshold=10
        )
        return render_template(
            "booking.html",
            doctor=doc,
            booking_mode=booking_mode,
            selected_date=selected_date.strftime("%Y-%m-%d"),
            available_slots=available_slots,
            show_queue_warning=show_queue_warning,
            demo_patients_ahead=demo_patients_ahead,
            today=date.today().strftime("%Y-%m-%d"),
            conflicting_appt=conflicting_appt,
        )

    # GET — prepare form data
    from datetime import timedelta
    default_date = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
    selected_date_str = request.args.get("date", default_date)
    try:
        selected_date = datetime.strptime(selected_date_str, "%Y-%m-%d").date()
        if selected_date < date.today():
            selected_date = date.today() + timedelta(days=1)
    except ValueError:
        selected_date = date.today() + timedelta(days=1)

    available_slots = appt_svc.get_available_slots(
        selected_date, filepath=app.config["APPOINTMENTS_FILE"]
    )

    # Pre-check: does this user already have an appointment on the selected date?
    conflicting_appt = appt_svc.get_user_appointment_on_date(
        current_user.user_id, selected_date, app.config["APPOINTMENTS_FILE"]
    )

    # Queue warning (demo)
    demo_patients_ahead = app.config.get("DEMO_PATIENTS_AHEAD_DEFAULT", 3)
    show_queue_warning = queue_svc.should_warn_before_booking(
        demo_patients_ahead, threshold=10
    )

    return render_template(
        "booking.html",
        doctor=doc,
        booking_mode=booking_mode,
        selected_date=selected_date.strftime("%Y-%m-%d"),
        available_slots=available_slots,
        show_queue_warning=show_queue_warning,
        demo_patients_ahead=demo_patients_ahead,
        today=date.today().strftime("%Y-%m-%d"),
        conflicting_appt=conflicting_appt,
    )


@app.route("/booking/confirmation/<appointment_id>")
@login_required
def booking_confirmation(appointment_id):
    appt = _get_appointment_or_404(appointment_id)
    _require_own_appointment(appt)
    queue_info = queue_svc.get_queue_position(appointment_id, app.config["APPOINTMENTS_FILE"])
    return render_template("booking_confirmation.html", appt=appt, queue_info=queue_info)


# ---------------------------------------------------------------------------
# Routes — Appointment management
# ---------------------------------------------------------------------------

@app.route("/my-appointments")
@login_required
def my_appointments():
    appts = appt_svc.get_user_appointments(
        current_user.user_id, app.config["APPOINTMENTS_FILE"]
    )
    today_str = date.today().strftime("%Y-%m-%d")
    upcoming = [a for a in appts
                if a.get("appointment_date", "") >= today_str
                and a.get("status") not in ("cancelled",)]
    completed = [a for a in appts
                 if a.get("appointment_date", "") < today_str
                 and a.get("status") not in ("cancelled",)]
    cancelled = [a for a in appts if a.get("status") == "cancelled"]
    return render_template(
        "my_appointments.html",
        upcoming=upcoming,
        completed=completed,
        cancelled=cancelled,
    )


@app.route("/appointment/<appointment_id>")
@login_required
def appointment_details(appointment_id):
    appt = _get_appointment_or_404(appointment_id)
    _require_own_appointment(appt)
    queue_info = queue_svc.get_queue_position(appointment_id, app.config["APPOINTMENTS_FILE"])

    # Check and send threshold notification if needed
    threshold = app.config.get("QUEUE_NOTIFICATION_THRESHOLD", 4)
    patients_ahead = queue_info.get("patients_ahead", 0) or 0
    if patients_ahead <= threshold and patients_ahead > 0:
        notif_svc.notify_queue_threshold(
            current_user.user_id, appointment_id, patients_ahead,
            app.config["NOTIFICATIONS_FILE"],
        )

    return render_template(
        "appointment_details.html",
        appt=appt,
        queue_info=queue_info,
        today=date.today().strftime("%Y-%m-%d"),
    )


@app.route("/appointment/<appointment_id>/cancel", methods=["POST"])
@login_required
def cancel_appointment(appointment_id):
    try:
        appt_svc.cancel_appointment(
            appointment_id, current_user.user_id, app.config["APPOINTMENTS_FILE"]
        )
        notif_svc.notify_booking_cancelled(
            current_user.user_id, appointment_id, app.config["NOTIFICATIONS_FILE"]
        )
        flash("Your appointment has been cancelled.", "success")
        logger.info("Appointment cancelled: id=%s user=%s", appointment_id, current_user.user_id)
    except PermissionError:
        abort(403)
    except ValueError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("my_appointments"))


@app.route("/appointment/<appointment_id>/reschedule", methods=["GET", "POST"])
@login_required
def reschedule_appointment(appointment_id):
    appt = _get_appointment_or_404(appointment_id)
    _require_own_appointment(appt)

    if appt.get("status") == "cancelled":
        flash("Cancelled appointments cannot be rescheduled.", "warning")
        return redirect(url_for("my_appointments"))

    from datetime import timedelta
    default_date = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")

    if request.method == "POST":
        new_date = request.form.get("appointment_date", "").strip()
        new_time = request.form.get("appointment_time", "").strip()
        try:
            updated = appt_svc.reschedule_appointment(
                appointment_id, current_user.user_id, new_date, new_time,
                app.config["APPOINTMENTS_FILE"],
            )
            notif_svc.notify_booking_rescheduled(
                current_user.user_id, appointment_id, new_date, new_time,
                app.config["NOTIFICATIONS_FILE"],
            )
            flash("Your appointment has been rescheduled.", "success")
            logger.info("Appointment rescheduled: id=%s", appointment_id)
            return redirect(url_for("appointment_details", appointment_id=appointment_id))
        except (ValueError, PermissionError) as exc:
            flash(str(exc), "danger")

    # GET
    selected_date_str = request.args.get("date", default_date)
    try:
        selected_date = datetime.strptime(selected_date_str, "%Y-%m-%d").date()
        if selected_date < date.today():
            selected_date = date.today() + timedelta(days=1)
    except ValueError:
        selected_date = date.today() + timedelta(days=1)

    available_slots = appt_svc.get_available_slots(
        selected_date,
        filepath=app.config["APPOINTMENTS_FILE"],
    )
    return render_template(
        "reschedule.html",
        appt=appt,
        selected_date=selected_date.strftime("%Y-%m-%d"),
        available_slots=available_slots,
        today=date.today().strftime("%Y-%m-%d"),
    )


@app.route("/queue/<appointment_id>")
@login_required
def queue_status(appointment_id):
    appt = _get_appointment_or_404(appointment_id)
    _require_own_appointment(appt)
    queue_info = queue_svc.get_queue_position(appointment_id, app.config["APPOINTMENTS_FILE"])
    return render_template("queue_status.html", appt=appt, queue_info=queue_info)


# ---------------------------------------------------------------------------
# Routes — Notifications
# ---------------------------------------------------------------------------

@app.route("/notifications")
@login_required
def notifications():
    notifs = notif_svc.get_user_notifications(
        current_user.user_id, app.config["NOTIFICATIONS_FILE"]
    )
    notif_svc.mark_all_read(current_user.user_id, app.config["NOTIFICATIONS_FILE"])
    return render_template("notifications.html", notifications=notifs)


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------

@app.errorhandler(403)
def forbidden(e):
    return render_template("403.html"), 403


@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


@app.errorhandler(500)
def internal_error(e):
    logger.exception("Internal server error: %s", e)
    return render_template("500.html"), 500


# ---------------------------------------------------------------------------
# AJAX helper — available slots
# ---------------------------------------------------------------------------

@app.route("/api/slots")
@login_required
def api_slots():
    date_str = request.args.get("date", "")
    exclude_id = request.args.get("exclude", "")
    try:
        selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"error": "Invalid date"}), 400
    slots = appt_svc.get_available_slots(selected_date, filepath=app.config["APPOINTMENTS_FILE"])
    return jsonify({"slots": slots})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=app.config["DEBUG"], host="127.0.0.1", port=5000)
