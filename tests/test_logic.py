import random
from datetime import date

import pytest

from app import (calculate_bmi, calculate_calories, generate_program,
                 membership_status, valid_iso_date)


@pytest.mark.parametrize("program,weight,expected", [
    ("Fat Loss (FL)", 80, 1760),
    ("Muscle Gain (MG)", 70, 2450),
    ("Beginner (BG)", 60, 1560),
])
def test_calories_per_program(program, weight, expected):
    assert calculate_calories(weight, program) == expected


def test_calories_rejects_bad_input():
    with pytest.raises(ValueError):
        calculate_calories(80, "Nope")
    with pytest.raises(ValueError):
        calculate_calories(0, "Fat Loss (FL)")


@pytest.mark.parametrize("h,w,category", [
    (180, 50, "Underweight"), (175, 70, "Normal"),
    (170, 80, "Overweight"), (165, 100, "Obese"),
])
def test_bmi_categories(h, w, category):
    assert calculate_bmi(h, w)[1] == category


def test_bmi_value_rounded():
    assert calculate_bmi(175, 80)[0] == 26.1


def test_bmi_invalid():
    with pytest.raises(ValueError):
        calculate_bmi(0, 70)


def test_membership_status():
    today = date(2026, 1, 1)
    assert membership_status("2026-06-01", today) == "Active"
    assert membership_status("2025-06-01", today) == "Expired"
    assert membership_status(None, today) == "Not Set"


def test_generate_program_shape_by_level():
    rng = random.Random(1)
    plan = generate_program("Muscle Gain (MG) - PPL", "advanced", rng)
    assert {p["day"] for p in plan} == {"Monday", "Tuesday", "Wednesday", "Thursday", "Friday"}
    assert all(4 <= p["sets"] <= 5 and 6 <= p["reps"] <= 15 for p in plan)
    assert len(plan) == 5 * 4


def test_generate_program_beginner_has_three_days():
    plan = generate_program("Beginner (BG)", "Beginner", random.Random(2))
    assert len({p["day"] for p in plan}) == 3


def test_generate_program_invalid_level():
    with pytest.raises(ValueError):
        generate_program("Beginner (BG)", "expert")


def test_valid_iso_date():
    assert valid_iso_date("2026-02-28")
    assert not valid_iso_date("28-02-2026")
    assert not valid_iso_date(None)
