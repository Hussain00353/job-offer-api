import requests
import http.client
import json
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import render

# ── RapidAPI credentials ─────────────────────────────────
RAPIDAPI_KEY = "36c39fceccmshff2a1cc9bbf72f5p1ccfa1jsn634879f450de"

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
        }

    except Exception:
        return None

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
    country   = 'Ireland'

    if not job_title or not city or not salary:
        return Response(
            {'error': 'Missing required fields'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # get market salary
    salary_data   = get_market_salary(job_title, city)
    market_salary = salary_data['median_salary'] if salary_data else 0

    # get cost of living
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
        job_title  = request.POST.get('job_title', '').strip()
        city       = request.POST.get('city', '').strip()
        salary_str = request.POST.get('gross_annual_salary', '').strip()
        country    = 'Ireland'

        # validate job title
        if not job_title or any(char.isdigit() for char in job_title):
            return render(request, 'analyser/index.html', {
                'error':  'Please enter a valid job title (no numbers)',
                'cities': IRISH_CITIES
            })

        # validate city
        if city not in IRISH_CITIES:
            return render(request, 'analyser/index.html', {
                'error':  'Please select a valid Irish city',
                'cities': IRISH_CITIES
            })

        # validate salary
        try:
            salary = int(salary_str)
            if salary < 10000 or salary > 999999:
                return render(request, 'analyser/index.html', {
                    'error':  'Please enter a salary between €10,000 and €999,999',
                    'cities': IRISH_CITIES
                })
        except:
            return render(request, 'analyser/index.html', {
                'error':  'Please enter a valid salary number',
                'cities': IRISH_CITIES
            })

        # get market salary
        salary_data = get_market_salary(job_title, city)

        # if job not found → show error
        if not salary_data:
            return render(request, 'analyser/index.html', {
                'error':  f'No salary data found for "{job_title}" in {city}. Please try a different job title.',
                'cities': IRISH_CITIES
            })

        market_salary = salary_data['median_salary']
        confidence    = salary_data['confidence']
        salary_count  = salary_data['salary_count']

        # get cost of living
        monthly_cost     = get_cost_of_living(city, country)
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
        }

        return render(request, 'analyser/results.html',
                     {'result': result})

    return render(request, 'analyser/index.html',
                 {'cities': IRISH_CITIES})