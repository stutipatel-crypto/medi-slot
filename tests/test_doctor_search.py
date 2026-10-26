"""
tests/test_doctor_search.py — Doctor directory and search tests.
"""

import json
from pathlib import Path

from services.doctor_service import get_all_doctors, get_doctor_by_id, search_doctors


def test_exactly_one_doctor(tmp_files):
    """Test 2: Exactly one doctor exists."""
    doctors = get_all_doctors(tmp_files["doctors"])
    assert len(doctors) == 1


def test_doctor_is_rawat(tmp_files):
    """Test 3: That doctor is Dr. Sanjiv Singh Rawat."""
    doctors = get_all_doctors(tmp_files["doctors"])
    assert doctors[0]["doctor_name"] == "Dr. Sanjiv Singh Rawat"


def test_no_other_doctor_in_search(tmp_files):
    """Test 4: No other doctor appears in search results."""
    results = search_doctors(filepath=tmp_files["doctors"])
    assert all(d["doctor_name"] == "Dr. Sanjiv Singh Rawat" for d in results)


def test_pediatrics_search_returns_doctor(tmp_files):
    """Test 5: Matching Pediatrics searches return Dr. Rawat."""
    results = search_doctors(
        city="Indore",
        specialization="Pediatrician",
        filepath=tmp_files["doctors"],
    )
    assert len(results) == 1
    assert results[0]["doctor_name"] == "Dr. Sanjiv Singh Rawat"


def test_pediatrics_variant_paediatrics(tmp_files):
    """Test 5b: 'Paediatrics' variant also matches."""
    results = search_doctors(specialization="Paediatrics", filepath=tmp_files["doctors"])
    assert len(results) == 1


def test_other_specialization_no_result(tmp_files):
    """Test 6: Other specializations return no doctor."""
    for spec in ["Cardiologist", "Dermatologist", "Orthopedic", "General Physician"]:
        results = search_doctors(specialization=spec, filepath=tmp_files["doctors"])
        assert results == [], f"Expected no results for {spec}, got {results}"


def test_unmatched_location_no_result(tmp_files):
    """Test 7: Unmatched locations return no doctor."""
    results = search_doctors(city="Mumbai", filepath=tmp_files["doctors"])
    assert results == []

    results = search_doctors(state="Maharashtra", filepath=tmp_files["doctors"])
    assert results == []

    results = search_doctors(country="USA", filepath=tmp_files["doctors"])
    assert results == []


def test_unknown_doctor_id_returns_none(tmp_files):
    """Test 8: Unknown doctor IDs return None (not a new record)."""
    assert get_doctor_by_id(999, tmp_files["doctors"]) is None
    assert get_doctor_by_id(0, tmp_files["doctors"]) is None
    assert get_doctor_by_id(2, tmp_files["doctors"]) is None


def test_unknown_doctor_id_returns_404(client):
    """Test 8b: Unknown doctor ID on the web returns 404."""
    resp = client.get("/doctor/999")
    assert resp.status_code == 404


def test_valid_doctor_id_returns_profile(client):
    """Doctor id=1 returns a profile page."""
    resp = client.get("/doctor/1")
    assert resp.status_code == 200
    assert b"Dr. Sanjiv Singh Rawat" in resp.data


def test_case_insensitive_city_search(tmp_files):
    """Location matching is case-insensitive."""
    results = search_doctors(city="indore", filepath=tmp_files["doctors"])
    assert len(results) == 1

    results = search_doctors(city="INDORE", filepath=tmp_files["doctors"])
    assert len(results) == 1


def test_medical_system_filter_no_result(tmp_files):
    """Medical system filter returns no result (classification not confirmed)."""
    results = search_doctors(
        medical_system="Modern Medicine",
        filepath=tmp_files["doctors"],
    )
    assert results == []
