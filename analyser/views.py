import os
import requests
import http.client
import json
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import render

# ── RapidAPI credentials ─────────────────────────────────
RAPIDAPI_KEY = os.environ.get('RAPIDAPI_KEY', '')

# ── Constants ─────────────────────────────────────────────
CLASSMATE_API_SOURCE = "Classmate API"
RAPIDAPI_SOURCE      = "RapidAPI"
INDEX_TEMPLATE       = 'analyser/index.html'
RESULTS_TEMPLATE     = 'analyser/results.html'

# ── Irish cities list ─────────────────────────────────────
IRISH_CITIES = [
    'Dublin',
    'Galway',
    'Cork',
    'Limerick',
]

# ── Helper: get market salary from Glassdoor ─────────────
def get_market_salary(job_title, city):
    try:
        conn = http.client.HTTPSConnection(
            "job-salary-data.p.rapidapi.com"
        )
        headers = {
            'x-rapidapi-key':  RAPIDAPI_KEY,
            'x-rapidapi-host': "job-salary-data.p.rapidapi.com"
        }
        location = f"{city} Ireland"
        url      = f"/job-salary?job_title={requests.utils.quote(job_title)}&location={requests.utils.quote(location)}&radius=25"
        conn.request("GET", url, headers=headers)
        res  = conn.getresponse()
        data = json.loads(res.read().decode("utf-8"))

        if not data.get('data'):
            return None

        salary_data = data['data'][0]
        return {
            'median_salary': round(salary_data['median_salary']),
            'min_salary':    round(salary_data['min_salary']),
            'max_salary':    round(salary_data['max_salary']),
            'confidence':    salary_data['confidence'],
            'salary_count':  salary_data['salary_count'],
            'salary_source': "Public API (Glassdoor via RapidAPI)",
        }

    except Exception:
        return None

# ── Helper: get cost of living from Classmate API ────────
def get_cost_of_living_classmate(city, country, salary, job_title):
    try:
        url     = "https://yj143x3irb.execute-api.us-east-1.amazonaws.com/get-data"
        payload = {
            "country": country.lower(),
            "city":    city,
            "salary":  salary,
            "job":     job_title
        }
        response = requests.post(url, json=payload, timeout=10)
        data     = response.json()
        if 'cost' in data:
            return round(data['cost'], 2)
        return None
    except Exception:
        return None

# ── Helper: get cost of living from RapidAPI (fallback) ──
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
        return round(
            rent + transport + utilities +
            internet + groceries + eating_out + entertainment
        , 2)
    except Exception:
        return 2960

# ── Helper: affordability score ──────────────────────────
def calculate_score(monthly_savings, monthly_income):
    if monthly_income <= 0:
        return 0
    if monthly_savings <= 0:
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

# ── Helper: get cost source ───────────────────────────────
def get_monthly_cost(city, country, salary, job_title):
    monthly_cost = get_cost_of_living_classmate(
        city, country, salary, job_title
    )
    if monthly_cost:
        return monthly_cost, CLASSMATE_API_SOURCE
    return get_cost_of_living(city, country), RAPIDAPI_SOURCE

# ── Helper: validate form inputs ─────────────────────────
def validate_inputs(job_title, city, salary_str):
    if not job_title or any(char.isdigit() for char in job_title):
        return None, 'Please enter a valid job title (no numbers)'
    if city not in IRISH_CITIES:
        return None, 'Please select a valid Irish city'
    try:
        salary = int(salary_str)
        if salary < 10000 or salary > 999999:
            return None, 'Please enter a salary between €10,000 and €999,999'
        return salary, None
    except ValueError:
        return None, 'Please enter a valid salary number'

# ── REST API view ─────────────────────────────────────────
@api_view(['POST'])
def analyse(request):
    data      = request.data
    job_title = data.get('job_title')
    city      = data.get('city')
    salary    = data.get('gross_annual_salary')
    country   = 'Ireland'

    if not job_title or not city or not salary:
        return Response(
            {'error': 'Missing required fields'},
            status=status.HTTP_400_BAD_REQUEST
        )

    salary_data   = get_market_salary(job_title, city)
    market_salary = salary_data['median_salary'] if salary_data else 0
    salary_source = salary_data['salary_source'] if salary_data else 'N/A'

    monthly_cost, cost_source = get_monthly_cost(
        city, country, salary, job_title
    )

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
        'recommendation':            recommendation,
        'salary_source':             salary_source,
        'cost_source':               cost_source,
    })

# ── Frontend views ────────────────────────────────────────
def index(request):
    if request.method == 'POST':
        job_title  = request.POST.get('job_title', '').strip()
        city       = request.POST.get('city', '').strip()
        salary_str = request.POST.get('gross_annual_salary', '').strip()
        country    = 'Ireland'

        salary, error = validate_inputs(job_title, city, salary_str)
        if error:
            return render(request, INDEX_TEMPLATE, {
                'error':  error,
                'cities': IRISH_CITIES
            })

        salary_data = get_market_salary(job_title, city)
        if not salary_data:
            return render(request, INDEX_TEMPLATE, {
                'error':  f'No salary data found for "{job_title}" in {city}. Please try a different job title.',
                'cities': IRISH_CITIES
            })

        market_salary = salary_data['median_salary']
        confidence    = salary_data['confidence']
        salary_count  = salary_data['salary_count']
        salary_source = salary_data['salary_source']

        monthly_cost, cost_source = get_monthly_cost(
            city, country, salary, job_title
        )

        salary_vs_market = salary - market_salary
        monthly_income   = round(salary / 12)
        monthly_savings  = round(monthly_income - monthly_cost)
        score            = calculate_score(monthly_savings, monthly_income)
        recommendation   = get_recommendation(score, salary_vs_market)

        result = {
            'job_title':                 job_title,
            'city':                      city,
            'country':                   country,
            'gross_annual_salary_eur':   salary,
            'market_average_salary_eur': market_salary,
            'salary_vs_market_eur':      salary_vs_market,
            'estimated_monthly_income':  monthly_income,
            'estimated_monthly_cost':    monthly_cost,
            'estimated_monthly_savings': monthly_savings,
            'affordability_score':       score,
            'recommendation':            recommendation,
            'confidence':                confidence,
            'salary_count':              salary_count,
            'salary_source':             salary_source,
            'cost_source':               cost_source,
        }

        return render(request, RESULTS_TEMPLATE, {'result': result})

    return render(request, INDEX_TEMPLATE, {'cities': IRISH_CITIES})

# ── Direct API view (for classmates) ─────────────────────
@api_view(['POST'])
def analyse_direct(request):
    data      = request.data
    job_title = data.get('job_title')
    city      = data.get('city')
    salary    = data.get('gross_annual_salary')
    country   = 'Ireland'

    if not job_title or not city or not salary:
        return Response(
            {'error': 'Missing required fields: job_title, city, gross_annual_salary'},
            status=status.HTTP_400_BAD_REQUEST
        )

    salary_data = get_market_salary(job_title, city)
    if not salary_data:
        return Response(
            {'error': f'No salary data found for "{job_title}" in {city}'},
            status=status.HTTP_404_NOT_FOUND
        )

    market_salary = salary_data['median_salary']
    confidence    = salary_data['confidence']
    salary_count  = salary_data['salary_count']
    salary_source = salary_data['salary_source']

    monthly_cost, cost_source = get_monthly_cost(
        city, country, salary, job_title
    )

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
        'recommendation':            recommendation,
        'confidence':                confidence,
        'salary_count':              salary_count,
        'salary_source':             salary_source,
        'cost_source':               cost_source,
    })
