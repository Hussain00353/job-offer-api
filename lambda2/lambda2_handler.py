import json
import requests
import http.client
import os

# ── credentials from environment variables ───────────────
RAPIDAPI_KEY = os.environ.get('RAPIDAPI_KEY')

# ── get market salary from Glassdoor ─────────────────────
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

# ── get cost of living from RapidAPI ─────────────────────
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

# ── Lambda handler ────────────────────────────────────────
def lambda_handler(event, context):
    try:
        job_title = event.get('job_title')
        city      = event.get('city')
        country   = event.get('country', 'Ireland')

        # call both APIs
        salary_data  = get_market_salary(job_title, city)
        monthly_cost = get_cost_of_living(city, country)

        # return data to Lambda 1
        return {
            'statusCode':   200,
            'salary_data':  salary_data,
            'monthly_cost': monthly_cost
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'error':      str(e)
        }