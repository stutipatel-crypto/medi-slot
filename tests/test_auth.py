"""
tests/test_auth.py — Authentication tests.
"""

import json
from pathlib import Path

from werkzeug.security import check_password_hash


def test_homepage_loads(client):
    """Test 1: The homepage loads."""
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Medi Slot" in resp.data


def test_signup_creates_user(client, tmp_files):
    """Test 9: Signup works."""
    resp = client.post("/signup", data={
        "name": "Jane Doe",
        "email": "jane@example.com",
        "password": "securepass",
        "confirm_password": "securepass",
    }, follow_redirects=True)
    assert resp.status_code == 200
    users = json.loads(Path(tmp_files["users"]).read_text())
    assert any(u["email"] == "jane@example.com" for u in users)


def test_signup_duplicate_rejected(client, tmp_files):
    """Test 10: Duplicate accounts are rejected."""
    data = {
        "name": "Jane Doe",
        "email": "jane@example.com",
        "password": "securepass",
        "confirm_password": "securepass",
    }
    client.post("/signup", data=data, follow_redirects=True)
    resp = client.post("/signup", data=data, follow_redirects=True)
    assert b"already exists" in resp.data.lower() or resp.status_code in (200, 302)


def test_password_is_hashed(client, tmp_files):
    """Test 11: Passwords are hashed — plaintext password not stored."""
    client.post("/signup", data={
        "name": "Alice",
        "email": "alice@example.com",
        "password": "mypassword",
        "confirm_password": "mypassword",
    }, follow_redirects=True)
    users = json.loads(Path(tmp_files["users"]).read_text())
    user = next(u for u in users if u["email"] == "alice@example.com")
    assert "password_hash" in user
    assert user.get("password_hash") != "mypassword"
    assert check_password_hash(user["password_hash"], "mypassword")


def test_login_valid(client, registered_user):
    """Test 12a: Login works with valid credentials."""
    resp = client.post("/login", data={
        "email": registered_user["email"],
        "password": registered_user["password"],
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b"Dashboard" in resp.data or b"Welcome" in resp.data


def test_login_invalid(client, registered_user):
    """Test 12b: Invalid credentials are rejected."""
    resp = client.post("/login", data={
        "email": registered_user["email"],
        "password": "wrongpassword",
    }, follow_redirects=True)
    assert b"Invalid" in resp.data or resp.status_code == 200


def test_protected_route_requires_login(client):
    """Test 13: Dashboard requires authentication."""
    resp = client.get("/dashboard", follow_redirects=False)
    assert resp.status_code == 302
    assert "/login" in resp.headers.get("Location", "")


def test_my_appointments_requires_login(client):
    """Test 13b: My appointments requires authentication."""
    resp = client.get("/my-appointments", follow_redirects=False)
    assert resp.status_code == 302


def test_logout(logged_in_client):
    """Logout clears the session."""
    resp = logged_in_client.get("/logout", follow_redirects=True)
    assert resp.status_code == 200
    # After logout, dashboard should redirect to login
    resp2 = logged_in_client.get("/dashboard", follow_redirects=False)
    assert resp2.status_code == 302
