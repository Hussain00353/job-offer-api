import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jobofferapi.settings')

import django
django.setup()

from analyser.views import calculate_score, get_recommendation

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
