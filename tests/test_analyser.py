import pytest
import sys
import os
from unittest.mock import patch, MagicMock

# ── Django setup ──────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['DJANGO_SETTINGS_MODULE'] = 'jobofferapi.settings'

import django
django.setup()

from rest_framework.test import APIClient
from django.test import Client
from django.urls import reverse

from analyser.views import (
    calculate_score,
    get_recommendation,
    validate_inputs,
    get_monthly_cost,
    get_market_salary,
    get_cost_of_living_classmate,
    get_cost_of_living,
)

client = APIClient()
django_client = Client()

# ── Test calculate_score ──────────────────────────────────
def test_calculate_score_high_savings():
    assert calculate_score(2754, 5417) == 100

def test_calculate_score_low_savings():
    score = calculate_score(500, 5417)
    assert 0 < score <= 100

def test_calculate_score_no_income():
    assert calculate_score(1000, 0) == 0

def test_calculate_score_negative_savings():
    assert calculate_score(-500, 5417) == 0


# ── Test get_recommendation ───────────────────────────────
def test_recommendation_excellent():
    assert get_recommendation(85, 5000) == "Excellent Offer"

def test_recommendation_good():
    rec = get_recommendation(70, -4000)
    assert rec == "Good Offer"

def test_recommendation_fair():
    rec = get_recommendation(50, -7000)
    assert rec == "Fair Offer - Try to Negotiate"

def test_recommendation_poor():
    assert get_recommendation(20, -20000) == "Poor Offer - Consider Declining"


# ── Test validate_inputs ──────────────────────────────────
def test_validate_valid_input():
    salary, error = validate_inputs("Cloud Engineer", "Dublin", "65000")
    assert salary == 65000
    assert error is None

def test_validate_invalid_job_title_numbers():
    salary, error = validate_inputs("Cloud123", "Dublin", "65000")
    assert salary is None

def test_validate_empty_job_title():
    salary, error = validate_inputs("", "Dublin", "65000")
    assert salary is None

def test_validate_invalid_city():
    salary, error = validate_inputs("Cloud Engineer", "London", "65000")
    assert salary is None

def test_validate_salary_too_low():
    salary, error = validate_inputs("Cloud Engineer", "Dublin", "100")
    assert salary is None

def test_validate_salary_too_high():
    salary, error = validate_inputs("Cloud Engineer", "Dublin", "9999999")
    assert salary is None

def test_validate_invalid_salary_string():
    salary, error = validate_inputs("Cloud Engineer", "Dublin", "abc")
    assert salary is None

def test_validate_valid_galway():
    salary, error = validate_inputs("Software Engineer", "Galway", "55000")
    assert salary == 55000

def test_validate_valid_cork():
    salary, error = validate_inputs("Data Analyst", "Cork", "45000")
    assert salary == 45000

def test_validate_valid_limerick():
    salary, error = validate_inputs("DevOps Engineer", "Limerick", "70000")
    assert salary == 70000


# ── Test get_monthly_cost ─────────────────────────────────
def test_get_monthly_cost_classmate_success():
    with patch('analyser.views.get_cost_of_living_classmate') as mock:
        mock.return_value = 2090.07
        cost, source = get_monthly_cost('Dublin', 'Ireland', 65000, 'Cloud Engineer')
        assert cost == 2090.07
        assert source == "Classmate API"

def test_get_monthly_cost_classmate_fallback():
    with patch('analyser.views.get_cost_of_living_classmate', return_value=None):
        with patch('analyser.views.get_cost_of_living', return_value=2662.66):
            cost, source = get_monthly_cost('Dublin', 'Ireland', 65000, 'Cloud Engineer')
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
        assert result['median_salary'] == 61000

def test_get_market_salary_no_data():
    mock_response = MagicMock()
    mock_response.read.return_value = b'{"data": []}'

    with patch('http.client.HTTPSConnection') as mock_conn:
        instance = mock_conn.return_value
        instance.getresponse.return_value = mock_response

        assert get_market_salary('Unknown', 'Dublin') is None

def test_get_market_salary_exception():
    with patch('http.client.HTTPSConnection', side_effect=Exception()):
        assert get_market_salary('Cloud Engineer', 'Dublin') is None


# ── Test get_cost_of_living_classmate ─────────────────────
def test_classmate_success():
    mock_response = MagicMock()
    mock_response.json.return_value = {'cost': 2090.07}

    with patch('requests.post', return_value=mock_response):
        assert get_cost_of_living_classmate('Dublin', 'Ireland', 65000, 'Cloud Engineer') == 2090.07

def test_classmate_no_cost():
    mock_response = MagicMock()
    mock_response.json.return_value = {}

    with patch('requests.post', return_value=mock_response):
        assert get_cost_of_living_classmate('Dublin', 'Ireland', 65000, 'Cloud Engineer') is None

def test_classmate_exception():
    with patch('requests.post', side_effect=Exception()):
        assert get_cost_of_living_classmate('Dublin', 'Ireland', 65000, 'Cloud Engineer') is None


# ── Test get_cost_of_living ───────────────────────────────
def test_cost_of_living_no_prices():
    mock_response = MagicMock()
    mock_response.read.return_value = b'{"error": "not found"}'

    with patch('http.client.HTTPSConnection') as mock_conn:
        instance = mock_conn.return_value
        instance.getresponse.return_value = mock_response

        assert get_cost_of_living('Dublin', 'Ireland') == 2960

def test_cost_of_living_exception():
    with patch('http.client.HTTPSConnection', side_effect=Exception()):
        assert get_cost_of_living('Dublin', 'Ireland') == 2960


# ── API VIEW TESTS (FIXED URLS) ───────────────────────────
@patch('analyser.views.get_market_salary')
@patch('analyser.views.get_monthly_cost')
def test_analyse_success(mock_cost, mock_salary):
    mock_salary.return_value = {'median_salary': 60000, 'salary_source': 'Mock'}
    mock_cost.return_value = (2000, "MockAPI")

    url = reverse('analyse')

    response = client.post(url, {
        'job_title': 'Cloud Engineer',
        'city': 'Dublin',
        'gross_annual_salary': 65000
    }, format='json')

    assert response.status_code == 200
    assert 'affordability_score' in response.data

def test_analyse_missing_fields():
    url = reverse('analyse')
    response = client.post(url, {}, format='json')
    assert response.status_code == 400


@patch('analyser.views.get_market_salary')
@patch('analyser.views.get_monthly_cost')
def test_analyse_direct_success(mock_cost, mock_salary):
    mock_salary.return_value = {
        'median_salary': 60000,
        'confidence': 'HIGH',
        'salary_count': 10,
        'salary_source': 'Mock'
    }
    mock_cost.return_value = (2000, "MockAPI")

    url = reverse('analyse_direct')

    response = client.post(url, {
        'job_title': 'Cloud Engineer',
        'city': 'Dublin',
        'gross_annual_salary': 65000
    }, format='json')

    assert response.status_code == 200

@patch('analyser.views.get_market_salary')
def test_analyse_direct_no_salary(mock_salary):
    mock_salary.return_value = None

    url = reverse('analyse_direct')

    response = client.post(url, {
        'job_title': 'Unknown',
        'city': 'Dublin',
        'gross_annual_salary': 65000
    }, format='json')

    assert response.status_code == 404


# ── DJANGO VIEW TESTS ─────────────────────────────────────
def test_index_get():
    response = django_client.get('/')
    assert response.status_code == 200

def test_index_invalid_input():
    response = django_client.post('/', {
        'job_title': '123',
        'city': 'Dublin',
        'gross_annual_salary': '65000'
    })
    assert response.status_code == 200


@patch('analyser.views.get_market_salary')
@patch('analyser.views.get_monthly_cost')
def test_index_success(mock_cost, mock_salary):
    mock_salary.return_value = {
        'median_salary': 60000,
        'confidence': 'HIGH',
        'salary_count': 10,
        'salary_source': 'Mock'
    }
    mock_cost.return_value = (2000, "MockAPI")

    response = django_client.post('/', {
        'job_title': 'Cloud Engineer',
        'city': 'Dublin',
        'gross_annual_salary': '65000'
    })

    assert response.status_code == 200
    assert b'Cloud Engineer' in response.content