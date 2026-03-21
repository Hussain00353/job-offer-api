import requests
import http.client
import json
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import render

# ── Adzuna API credentials ──────────────────────────────
ADZUNA_APP_ID  = "ccd8eda6"
ADZUNA_APP_KEY = "16f9d33fa4852b1bd77dd2f038d69648"

# ── RapidAPI credentials ─────────────────────────────────
RAPIDAPI_KEY   = "36c39fceccmshff2a1cc9bbf72f5p1ccfa1jsn634879f450de"

# ── Helper: get market salary from Adzuna ────────────────
def get_market_salary(job_title, city):
    url = "https://api.adzuna.com/v1/api/jobs/gb/histogram"

    params = {
        'app_id':       ADZUNA_APP_ID,
        'app_key':      ADZUNA_APP_KEY,
        'what':         job_title,
        'where':        city,
        'content-type': 'application/json'
    }

    try:
        response  = requests.get(url, params=params, timeout=10)
        data      = response.json()
        histogram = data.get('histogram', {})

        if not histogram:
            return 72000

        total_jobs   = 0
        total_salary = 0

        for salary_str, count in histogram.items():
            salary        = int(salary_str)
            total_salary += salary * count
            total_jobs   += count

        return round(total_salary / total_jobs)

    except Exception:
        return 72000

# ── Helper: get cost of living from RapidAPI ─────────────
def get_cost_of_living(city, country):
    try:
        conn = http.client.HTTPSConnection(
            "cost-of-living-and-prices.p.rapidapi.com"
        )

        headers = {
            'x-rapidapi-key':  RAPIDAPI_KEY,
            'x-rapidapi-host': "cost-of-living-and-prices.p.rapidapi.com"
        }

        conn.request(
            "GET",
            f"/prices?city_name={city}&country_name={country}",
            headers=headers
        )

        res  = conn.getresponse()
        data = json.loads(res.read().decode("utf-8"))

        if 'prices' not in data:
            return 2960

        prices = data['prices']

        def get_by_id(good_id):
            item = next(
                (p for p in prices if p['good_id'] == good_id), None
            )
            return round(item['avg'], 2) if item else 0

        rent      = get_by_id(29)
        transport = get_by_id(46)
        utilities = get_by_id(54)
        internet  = get_by_id(55)

        groceries = round(
            get_by_id(11) * 6  +
            get_by_id(13) * 6  +
            get_by_id(20) * 30 +
            get_by_id(15) * 12 +
            get_by_id(18) * 16 +
            get_by_id(9)  * 8  +
            get_by_id(25) * 6  +
            get_by_id(26) * 6  +
            get_by_id(21) * 6  +
            get_by_id(24) * 6  +
            get_by_id(19) * 3  +
            get_by_id(27) * 20 +
            get_by_id(10) * 4  +
            get_by_id(22) * 4  +
            get_by_id(14) * 8
        , 2)

        eating_out    = round(get_by_id(38) * 12, 2)
        entertainment = round(get_by_id(42) * 2 + get_by_id(43), 2)

        total = round(
            rent + transport + utilities +
            internet + groceries + eating_out + entertainment
        , 2)

        return total

    except Exception:
        return 2960

# ── Helper: affordability score ──────────────────────────
def calculate_score(monthly_savings, monthly_income):
    if monthly_income <= 0:
        return 0
    return min(100, round((monthly_savings / monthly_income) * 200))

# ── Helper: recommendation ───────────────────────────────
def get_recommendation(score, salary_vs_market):
    if score >= 80 and salary_vs_market >= 0:
        return "Excellent Offer"
    elif score >= 60 and salary_vs_market >= -10000:
        return "Good Offer"
    elif score >= 40:
        return "Fair Offer - Try to Negotiate"
    else:
        return "Poor Offer - Consider Declining"

# ── REST API view ─────────────────────────────────────────
@api_view(['POST'])
def analyse(request):

    data      = request.data
    job_title = data.get('job_title')
    city      = data.get('city')
    salary    = data.get('gross_annual_salary')
    country   = data.get('country', 'Ireland')

    if not job_title or not city or not salary:
        return Response(
            {'error': 'Missing required fields'},
            status=status.HTTP_400_BAD_REQUEST
        )

    market_salary    = get_market_salary(job_title, city)
    monthly_cost     = get_cost_of_living(city, country)
    salary_vs_market = salary - market_salary
    monthly_income   = round(salary / 12)
    monthly_savings  = round(monthly_income - monthly_cost)
    score            = calculate_score(monthly_savings, monthly_income)
    recommendation   = get_recommendation(score, salary_vs_market)

    return Response({
        'job_title':                 job_title,
        'city':                      city,
        'gross_annual_salary_eur':   salary,
        'market_average_salary_eur': market_salary,
        'salary_vs_market_eur':      salary_vs_market,
        'estimated_monthly_income':  monthly_income,
        'estimated_monthly_cost':    monthly_cost,
        'estimated_monthly_savings': monthly_savings,
        'affordability_score':       score,
        'recommendation':            recommendation
    })

# ── Frontend views ────────────────────────────────────────
def index(request):
    if request.method == 'POST':
        job_title  = request.POST.get('job_title')
        city       = request.POST.get('city')
        country    = request.POST.get('country', 'Ireland')
        salary_str = request.POST.get('gross_annual_salary')

        try:
            salary = int(salary_str)
        except:
            return render(request, 'analyser/index.html',
                         {'error': 'Please enter a valid salary'})

        market_salary    = get_market_salary(job_title, city)
        monthly_cost     = get_cost_of_living(city, country)
        salary_vs_market = salary - market_salary
        monthly_income   = round(salary / 12)
        monthly_savings  = round(monthly_income - monthly_cost)
        score            = calculate_score(monthly_savings, monthly_income)
        recommendation   = get_recommendation(score, salary_vs_market)

        result = {
            'job_title':                 job_title,
            'city':                      city,
            'gross_annual_salary_eur':   salary,
            'market_average_salary_eur': market_salary,
            'salary_vs_market_eur':      salary_vs_market,
            'estimated_monthly_income':  monthly_income,
            'estimated_monthly_cost':    monthly_cost,
            'estimated_monthly_savings': monthly_savings,
            'affordability_score':       score,
            'recommendation':            recommendation
        }

        return render(request, 'analyser/results.html',
                     {'result': result})

    return render(request, 'analyser/index.html')