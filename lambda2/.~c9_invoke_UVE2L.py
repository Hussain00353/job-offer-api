import json
import requests
import http.client
import os

# ── credentials ───────────────────────────────────────────
RAPIDAPI_KEY = os.environ.get('RAPIDAPI_KEY', '')

# ── get market salary from JSearch ───────────────────────
def get_market_salary(job_title, city):
    try:
        conn    = http.client.HTTPSConnection("jsearch.p.rapidapi.com")
        headers = {
            'x-rapidapi-key':  RAPIDAPI_KEY,
            'x-rapidapi-host': "jsearch.p.rapidapi.com"
        }
        location = f"{city}, Ireland"
        url      = f"/estimated-salary?job_title={requests.utils.quote(job_title)}&location={requests.utils.quote(location)}&radius=100"
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
            'salary_source': "Public API (Glassdoor via JSearch)",
        }

    except Exception:
        return None

# ── get cost of living from Classmate API ────────────────
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

# ── get cost of living from RapidAPI (fallback) ──────────
def get_cost_of_living(city, country):
    try:
        conn    = http.client.HTTPSConnection(
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

# ── calculate Irish net monthly salary (2026) ────────────
def calculate_net_salary(gross_annual):

    # PAYE
    if gross_annual <= 42000:
        paye = gross_annual * 0.20
    else:
        paye = (42000 * 0.20) + ((gross_annual - 42000) * 0.40)
    paye = max(0, paye - 3750)

    # USC
    if gross_annual <= 12012:
        usc = gross_annual * 0.005
    elif gross_annual <= 25760:
        usc = (12012 * 0.005) + \
              ((gross_annual - 12012) * 0.02)
    elif gross_annual <= 70044:
        usc = (12012 * 0.005) + \
              ((25760 - 12012) * 0.02) + \
              ((gross_annual - 25760) * 0.04)
    else:
        usc = (12012 * 0.005) + \
              ((25760 - 12012) * 0.02) + \
              ((70044 - 25760) * 0.04) + \
              ((gross_annual - 70044) * 0.08)

    # PRSI
    prsi = gross_annual * 0.04

    net_annual = gross_annual - paye - usc - prsi
    return {
        'gross_monthly': round(gross_annual / 12, 2),
        'paye_monthly':  round(paye / 12, 2),
        'usc_monthly':   round(usc / 12, 2),
        'prsi_monthly':  round(prsi / 12, 2),
        'net_monthly':   round(net_annual / 12, 2),
    }

# ── Lambda handler ────────────────────────────────────────
def lambda_handler(event, context):
    try:
        job_title = event.get('job_title')
        city      = event.get('city')
        salary    = event.get('gross_annual_salary', 0)
        country   = event.get('country', 'Ireland')

        # get market salary
        salary_data = get_market_salary(job_title, city)

        # get cost of living
        monthly_cost = get_cost_of_living_classmate(
            city, country, salary, job_title
        )
        if monthly_cost:
            cost_source = "Classmate API"
        else:
            monthly_cost = get_cost_of_living(city, country)
            cost_source  = "RapidAPI"

        # calculate tax
        tax_breakdown = calculate_net_salary(salary)

        return {
            'statusCode':   200,
            'salary_data':  salary_data,
            'monthly_cost': monthly_cost,
            'cost_source':  cost_source,
            'tax_breakdown': tax_breakdown,
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'error':      str(e)
        }
