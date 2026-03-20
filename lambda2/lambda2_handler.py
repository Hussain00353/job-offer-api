import json
import requests
import http.client
import os

# ── credentials from environment variables ───────────────
ADZUNA_APP_ID  = os.environ.get('ADZUNA_APP_ID')
ADZUNA_APP_KEY = os.environ.get('ADZUNA_APP_KEY')
RAPIDAPI_KEY   = os.environ.get('RAPIDAPI_KEY')

# ── get market salary from Adzuna ────────────────────────
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
            return 72000  # fallback

        total_jobs   = 0
        total_salary = 0

        for salary_str, count in histogram.items():
            salary        = int(salary_str)
            total_salary += salary * count
            total_jobs   += count

        return round(total_salary / total_jobs)

    except Exception:
        return 72000  # fallback

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
            return 2960  # fallback

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
        return 2960  # fallback

# ── Lambda handler ────────────────────────────────────────
def lambda_handler(event, context):
    try:
        # get inputs
        job_title = event.get('job_title')
        city      = event.get('city')
        country   = event.get('country', 'Ireland')

        # call both APIs
        market_salary = get_market_salary(job_title, city)
        monthly_cost  = get_cost_of_living(city, country)

        # return data to Lambda 1
        return {
            'statusCode':    200,
            'market_salary': market_salary,
            'monthly_cost':  monthly_cost
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'error':      str(e)
        }