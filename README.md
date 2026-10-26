# Medi Slot — Doctor Search & Appointment Booking

A full-stack web application built with Python Flask.

> **⚠️ DEMO MODE:** All bookings are simulated. The clinic has not been
> contacted or authorized to receive bookings. All profile information
> requires independent verification.

---

## 🏥 About This Project

Medi Slot is a doctor search and appointment booking platform.

**Currently listed doctor:** Dr. Sanjiv Singh Rawat  
**Specialization:** Pediatrician  
**Clinic:** Child Care Hospital, Tilak Nagar, Indore, Madhya Pradesh, India

---

## 🚀 Quick Start (Windows)

### Step 1 — Open the project folder

Open PowerShell and navigate to the project:

```powershell
cd d:\medislot1
```

### Step 2 — Create a virtual environment (recommended)

```powershell
py -m venv .venv
```

### Step 3 — Activate the virtual environment

```powershell
.\.venv\Scripts\Activate.ps1
```

> **If activation fails with a PowerShell policy error**, run this safe alternative
> *for this session only* (does not change system settings permanently):
>
> ```powershell
> Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
> .\.venv\Scripts\Activate.ps1
> ```

### Step 4 — Install packages

```powershell
py -m pip install -r requirements.txt
```

### Step 5 — Configure environment variables (optional for development)

Copy `.env.example` to `.env`:

```powershell
Copy-Item .env.example .env
```

The default development configuration works without a `.env` file.
For production, set a strong `SECRET_KEY` in `.env`.

### Step 6 — Start the application

```powershell
py app.py
```

### Step 7 — Open the website

Visit [http://127.0.0.1:5000/](http://127.0.0.1:5000/) in your browser.

---

## 🧪 Running Tests

```powershell
py -m pytest -v
```

All 40 tests should pass.  Tests use isolated temporary files —
they never modify your real `appointments.txt` or `users.txt`.

---

## 📁 Project Structure

```
medislot1/
├── app.py                  ← Main Flask application (routes + auth)
├── config.py               ← Configuration (env vars, file paths, modes)
├── requirements.txt        ← Python dependencies
├── .env.example            ← Environment variable template
├── doctors.txt             ← Dr. Sanjiv Singh Rawat's record (JSON)
├── users.txt               ← Registered users (JSON array)
├── appointments.txt        ← Booked appointments (JSON array)
├── notifications.txt       ← In-app notifications (JSON array)
│
├── services/
│   ├── storage.py          ← JSON file read/write helpers
│   ├── doctor_service.py   ← Doctor search and lookup
│   ├── appointment_service.py ← Booking, cancellation, rescheduling
│   ├── queue_service.py    ← Demo queue calculations
│   └── notification_service.py ← In-app notification management
│
├── templates/              ← Jinja2 HTML templates
│   ├── base.html           ← Shared layout, navbar, footer
│   ├── index.html          ← Homepage + hero search
│   ├── login.html          ← Login page
│   ├── signup.html         ← Sign-up page
│   ├── dashboard.html      ← User dashboard
│   ├── search_doctors.html ← Search results
│   ├── doctor_profile.html ← Full doctor profile
│   ├── booking.html        ← Booking form
│   ├── booking_confirmation.html
│   ├── my_appointments.html
│   ├── appointment_details.html
│   ├── reschedule.html
│   ├── queue_status.html
│   ├── notifications.html
│   ├── 403.html / 404.html / 500.html
│   └── _appt_card.html     ← Reusable appointment card
│
├── static/
│   ├── css/style.css       ← All styles (blue/white/grey scheme)
│   ├── js/main.js          ← Nav, password toggle, slot loading
│   └── images/             ← SVG logo + placeholder
│
└── tests/
    ├── conftest.py         ← Fixtures with isolated temp files
    ├── test_auth.py        ← Signup, login, logout, sessions
    ├── test_doctor_search.py ← Doctor directory and search
    ├── test_appointments.py  ← Booking, cancellation, rescheduling
    └── test_queue.py         ← Queue, notifications, storage safety
```

---

## 🌐 Available Pages

| URL | Description |
|-----|-------------|
| `/` | Homepage with search form |
| `/doctors` | Search and filter doctors |
| `/doctor/1` | Dr. Sanjiv Singh Rawat's profile |
| `/signup` | Create a new account |
| `/login` | Log in |
| `/logout` | Log out |
| `/dashboard` | Your appointment dashboard |
| `/book/1` | Book a demo appointment |
| `/my-appointments` | View all your appointments |
| `/appointment/<id>` | Appointment details |
| `/appointment/<id>/cancel` | Cancel an appointment |
| `/appointment/<id>/reschedule` | Reschedule an appointment |
| `/queue/<id>` | Demo queue status |
| `/notifications` | In-app notification centre |
| `/health` | Server health check (JSON) |

---

## 🔧 Configuration Options

Edit `.env` to change these settings:

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | `dev-only-...` | **Change in production** |
| `BOOKING_MODE` | `demo` | `demo` or `live` (live requires clinic auth) |
| `QUEUE_MODE` | `demo` | Queue mode |
| `QUEUE_NOTIFICATION_THRESHOLD` | `4` | Patients-ahead count to trigger alert |
| `DEFAULT_APPOINTMENT_DURATION_MINUTES` | `15` | Demo slot duration |
| `FLASK_DEBUG` | `true` | Set `false` in production |

---

## ⚠️ Data Verification Notices

The following information is **user-supplied** and has not been independently verified:

- **Area vs Address discrepancy:** Area is listed as "Tilak Nagar" but the address mentions "Bakhtawar Ram Nagar". Both values are preserved.
- **Consultation fee** of ₹600 must be reconfirmed before any live bookings.
- **Visiting hours** must be confirmed before treating as real availability.
- **Video consultation** availability is unknown.
- **Clinic booking authorization** has not been obtained.

---

## 🔒 Before Enabling Live Bookings

Live booking (`BOOKING_MODE=live`) requires:

1. Written authorization from Child Care Hospital / Dr. Sanjiv Singh Rawat.
2. Confirmed and live-verified visiting hours.
3. A real-time availability data source from the clinic.
4. Reconfirmed consultation fee.
5. A strong `SECRET_KEY` in production environment variables.
6. HTTPS deployment with `SESSION_COOKIE_SECURE=true`.
7. (Optional) A real notification provider for SMS/email alerts.

---

## 🛠️ Troubleshooting

**Problem:** `ModuleNotFoundError: No module named 'flask'`  
**Fix:** Make sure your virtual environment is activated and run `py -m pip install -r requirements.txt`.

**Problem:** PowerShell says "cannot be loaded because running scripts is disabled"  
**Fix:** Run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in the same PowerShell window.

**Problem:** Port 5000 is already in use  
**Fix:** Change the port in `app.py`:  `app.run(..., port=5001)`

**Problem:** `doctors.txt` shows a warning in the logs  
**Fix:** Make sure `doctors.txt` contains exactly the one supplied doctor record (id=1).

**Problem:** Tests fail with "file not found"  
**Fix:** Run tests from the project root: `cd d:\medislot1; py -m pytest -v`

---

## 📋 Storage Notes

Data is stored as JSON arrays in `.txt` files. Limitations:
- Not designed for multiple simultaneous users in production.
- No transaction support or rollback.
- Migrate to SQLite or MySQL for production by implementing the storage service layer.
- Files are **never reset** on Flask restart — your appointment data is preserved.

---

*Medi Slot — currently in demo/development mode.*
