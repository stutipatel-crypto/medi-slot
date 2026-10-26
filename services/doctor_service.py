"""
services/doctor_service.py — Business logic for the doctor directory.

IMPORTANT:
  The active doctor directory contains EXACTLY ONE doctor:
  Dr. Sanjiv Singh Rawat (id=1).

  This module NEVER creates additional doctors, seeds fake records,
  or invents data beyond what is stored in doctors.txt.
"""

from pathlib import Path
from services.storage import read_json

# Lazily resolved at call time so tests can override the path.
_DEFAULT_DOCTORS_FILE = Path(__file__).parent.parent / "doctors.txt"


def _doctors_file(filepath=None):
    return filepath or _DEFAULT_DOCTORS_FILE


def get_all_doctors(filepath=None) -> list:
    """Return all doctor records.  Should always be a single-item list."""
    return read_json(_doctors_file(filepath))


def get_doctor_by_id(doctor_id: int, filepath=None) -> dict | None:
    """
    Return the doctor record whose 'id' equals *doctor_id*, or None.
    Does NOT create a record when one is not found.
    """
    for doc in read_json(_doctors_file(filepath)):
        if doc.get("id") == doctor_id:
            return doc
    return None


# ---------------------------------------------------------------------------
# Search / filtering
# ---------------------------------------------------------------------------

def _normalize(value) -> str:
    """Strip whitespace and lowercase for case-insensitive comparison."""
    return str(value).strip().lower() if value else ""


def search_doctors(
    *,
    country: str = "",
    state: str = "",
    city: str = "",
    area: str = "",
    specialization: str = "",
    medical_system: str = "",
    filepath=None,
) -> list:
    """
    Filter the doctor list by the supplied criteria.

    Rules:
    - Each non-empty filter must match the corresponding doctor field.
    - Matching is case-insensitive with whitespace normalisation.
    - The medical-system field is not confirmed for the current doctor, so
      a non-empty medical_system filter will return no results unless the
      doctor record explicitly confirms the classification.
    - Returns only records from doctors.txt — no invented records.
    """
    doctors = read_json(_doctors_file(filepath))
    results = []

    for doc in doctors:
        # Skip any record that is not the authorised single doctor.
        # (Defensive check: the file should only ever have id=1.)
        if doc.get("id") != 1:
            continue

        # --- Location filters ---
        if country and _normalize(country) != _normalize(doc.get("country", "")):
            continue
        if state and _normalize(state) != _normalize(doc.get("state", "")):
            continue
        if city and _normalize(city) != _normalize(doc.get("city", "")):
            continue
        if area and _normalize(area) not in (
            _normalize(doc.get("area", "")),
            _normalize(doc.get("city", "")),
        ):
            continue

        # --- Specialization filter ---
        if specialization:
            spec_input = _normalize(specialization)
            spec_stored = _normalize(doc.get("specialization", ""))
            # Accept common variants: pediatrician, pediatrics, paediatrics, paediatrician
            pediatric_variants = {"pediatrician", "pediatrics", "paediatrician", "paediatrics"}
            match = False
            if spec_input == spec_stored:
                match = True
            elif spec_input in pediatric_variants and spec_stored in pediatric_variants:
                match = True
            if not match:
                continue

        # --- Medical system filter ---
        # The doctor record does not confirm a medical-system classification.
        # A non-empty medical_system filter therefore produces no results
        # (consistent with requirement: do not auto-assign a classification).
        if medical_system and _normalize(medical_system) not in ("", "all", "any"):
            confirmed_system = _normalize(doc.get("medical_system", ""))
            if not confirmed_system or _normalize(medical_system) != confirmed_system:
                continue

        results.append(doc)

    return results
