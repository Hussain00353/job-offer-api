import pytest
import sys
import os
from unittest.mock import patch, MagicMock

# ── Django setup ──────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['DJANGO_SETTINGS_MODULE'] = 'jobofferapi.settings'

import django
django.setup()

from analyser.views import (
    calculate_score,
    get_recommendation,
    validate_inputs,
    get_monthly_cost,
    get_market_salary,
    get_cost_of_living_classmate,
    get_cost_of_living,
)

# ── Test calculate_score ──────────────────────────────────
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

# ── Test get_recommendation ───────────────────────────────
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

# ── Test get_monthly_cost ─────────────────────────────────
def test_get_monthly_cost_classmate_success():
    with patch('analyser.views.get_cost_of_living_classmate') as mock:
        mock.return_value = 2090.07
        cost, source = get_monthly_cost(
            'Dublin', 'Ireland', 65000, 'Cloud Engineer'
        )
        assert cost == 2090.07
        assert source == "Classmate API"

def test_get_monthly_cost_classmate_fails_uses_rapidapi():
    with patch('analyser.views.get_cost_of_living_classmate') as mock_c:
        with patch('analyser.views.get_cost_of_living') as mock_r:
            mock_c.return_value = None
            mock_r.return_value = 2662.66
            cost, source = get_monthly_cost(
                'Dublin', 'Ireland', 65000, 'Cloud Engineer'
            )
            assert cost == 2662.66
            assert source == "RapidAPI"

# ── Test get_market_salary ────────────────────────────────
def test_get_market_salary_success():
    mock_response = MagicMock()
    mock_response.read.return_value = b'''{
        "data": [{
            "median_salary": 61000,
            "min_salary": 51250,
            "max_salary": 72750,
            "confidence": "VERY_HIGH",
            "salary_count": 122
        }]
    }'''
    with patch('http.client.HTTPSConnection') as mock_conn:
        instance = mock_conn.return_value
        instance.getresponse.return_value = mock_response
        result = get_market_salary('Cloud Engineer', 'Dublin')
        assert result is not None
        assert result['median_salary'] == 61000
        assert result['confidence'] == 'VERY_HIGH'

def test_get_market_salary_no_data():
    mock_response = MagicMock()
    mock_response.read.return_value = b'{"data": []}'
    with patch('http.client.HTTPSConnection') as mock_conn:
        instance = mock_conn.return_value
        instance.getresponse.return_value = mock_response
        result = get_market_salary('Unknown Job', 'Dublin')
        assert result is None

def test_get_market_salary_exception():
    with patch('http.client.HTTPSConnection') as mock_conn:
        mock_conn.side_effect = Exception("Connection error")
        result = get_market_salary('Cloud Engineer', 'Dublin')
        assert result is None

# ── Test get_cost_of_living_classmate ─────────────────────
def test_get_cost_of_living_classmate_success():
    mock_response = MagicMock()
    mock_response.json.return_value = {'cost': 2090.07}
    with patch('requests.post', return_value=mock_response):
        result = get_cost_of_living_classmate(
            'Dublin', 'Ireland', 65000, 'Cloud Engineer'
        )
        assert result == 2090.07

def test_get_cost_of_living_classmate_no_cost():
    mock_response = MagicMock()
    mock_response.json.return_value = {'error': 'not found'}
    with patch('requests.post', return_value=mock_response):
        result = get_cost_of_living_classmate(
            'Dublin', 'Ireland', 65000, 'Cloud Engineer'
        )
        assert result is None

def test_get_cost_of_living_classmate_exception():
    with patch('requests.post', side_effect=Exception("error")):
        result = get_cost_of_living_classmate(
            'Dublin', 'Ireland', 65000, 'Cloud Engineer'
        )
        assert result is None

# ── Test get_cost_of_living ───────────────────────────────
def test_get_cost_of_living_success():
    mock_response = MagicMock()
    mock_response.read.return_value = b'''{
        "prices": [
            {"good_id": 29, "avg": 1695.68},
            {"good_id": 46, "avg": 134.60},
            {"good_id": 54, "avg": 157.18},
            {"good_id": 55, "avg": 52.45},
            {"good_id": 11, "avg": 10.75},
            {"good_id": 13, "avg": 8.46},
            {"good_id": 20, "avg": 1.07},
            {"good_id": 15, "avg": 3.16},
            {"good_id": 18, "avg": 1.53},
            {"good_id": 9,  "avg": 2.24},
            {"good_id": 25, "avg": 1.64},
            {"good_id": 26, "avg": 2.71},
            {"good_id": 21, "avg": 1.23},
            {"good_id": 24, "avg": 1.61},
            {"good_id": 19, "avg": 10.35},
            {"good_id": 27, "avg": 1.51},
            {"good_id": 10, "avg": 1.98},
            {"good_id": 22, "avg": 2.51},
            {"good_id": 14, "avg": 2.62},
            {"good_id": 38, "avg": 15.48},
            {"good_id": 42, "avg": 12.39},
            {"good_id": 43, "avg": 41.22}
        ]
    }'''
    with patch('http.client.HTTPSConnection') as mock_conn:
        instance = mock_conn.return_value
        instance.getresponse.return_value = mock_response
        result = get_cost_of_living('Dublin', 'Ireland')
        assert result > 0

def test_get_cost_of_living_no_prices():
    mock_response = MagicMock()
    mock_response.read.return_value = b'{"error": "not found"}'
    with patch('http.client.HTTPSConnection') as mock_conn:
        instance = mock_conn.return_value
        instance.getresponse.return_value = mock_response
        result = get_cost_of_living('Dublin', 'Ireland')
        assert result == 2960

def test_get_cost_of_living_exception():
    with patch('http.client.HTTPSConnection') as mock_conn:
        mock_conn.side_effect = Exception("Connection error")
        result = get_cost_of_living('Dublin', 'Ireland')
        assert result == 2960
