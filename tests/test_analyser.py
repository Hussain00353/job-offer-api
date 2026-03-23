import pytest
import sys
import os

# ── Django setup ──────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['DJANGO_SETTINGS_MODULE'] = 'jobofferapi.settings'

import django
django.setup()

from analyser.views import (
    calculate_score,
    get_recommendation,
    validate_inputs
)

# ── Test affordability score ──────────────────────────────
def test_calculate_score_high_savings():
    score = calculate_score(2754, 5417)
    assert score == 100

def test_calculate_score_low_savings():
    score = calculate_score(500, 5417)
    assert score > 0
    assert score <= 100

def test_calculate_score_no_income():
    score = calculate_score(1000, 0)
    assert score == 0

def test_calculate_score_negative_savings():
    score = calculate_score(-500, 5417)
    assert score == 0

# ── Test recommendation ───────────────────────────────────
def test_recommendation_excellent():
    rec = get_recommendation(85, 5000)
    assert rec == "Excellent Offer"

def test_recommendation_good():
    rec = get_recommendation(70, -5000)
    assert rec == "Good Offer"

def test_recommendation_fair():
    rec = get_recommendation(50, -15000)
    assert rec == "Fair Offer - Try to Negotiate"

def test_recommendation_poor():
    rec = get_recommendation(20, -20000)
    assert rec == "Poor Offer - Consider Declining"

# ── Test validate_inputs ──────────────────────────────────
def test_validate_valid_input():
    salary, error = validate_inputs("Cloud Engineer", "Dublin", "65000")
    assert salary == 65000
    assert error is None

def test_validate_invalid_job_title_numbers():
    salary, error = validate_inputs("Cloud123", "Dublin", "65000")
    assert salary is None
    assert error is not None

def test_validate_empty_job_title():
    salary, error = validate_inputs("", "Dublin", "65000")
    assert salary is None
    assert error is not None

def test_validate_invalid_city():
    salary, error = validate_inputs("Cloud Engineer", "London", "65000")
    assert salary is None
    assert error is not None

def test_validate_salary_too_low():
    salary, error = validate_inputs("Cloud Engineer", "Dublin", "100")
    assert salary is None
    assert error is not None

def test_validate_salary_too_high():
    salary, error = validate_inputs("Cloud Engineer", "Dublin", "9999999")
    assert salary is None
    assert error is not None

def test_validate_invalid_salary_string():
    salary, error = validate_inputs("Cloud Engineer", "Dublin", "abc")
    assert salary is None
    assert error is not None

def test_validate_valid_galway():
    salary, error = validate_inputs("Software Engineer", "Galway", "55000")
    assert salary == 55000
    assert error is None

def test_validate_valid_cork():
    salary, error = validate_inputs("Data Analyst", "Cork", "45000")
    assert salary == 45000
    assert error is None

def test_validate_valid_limerick():
    salary, error = validate_inputs("DevOps Engineer", "Limerick", "70000")
    assert salary == 70000
    assert error is None