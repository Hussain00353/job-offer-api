import requests

APP_ID  = "ccd8eda6"
APP_KEY = "16f9d33fa4852b1bd77dd2f038d69648"

def get_market_salary(job_title, city):
    url = "https://api.adzuna.com/v1/api/jobs/gb/histogram"
    
    params = {
        'app_id':       APP_ID,
        'app_key':      APP_KEY,
        'what':         job_title,
        'where':        city,
        'content-type': 'application/json'
    }
    
    response = requests.get(url, params=params)
    data     = response.json()

    # extract histogram
    histogram = data.get('histogram', {})

    if not histogram:
        return 72000  # fallback if API fails

    # calculate weighted average
    total_jobs   = 0
    total_salary = 0

    for salary_str, count in histogram.items():
        salary       = int(salary_str)
        total_salary += salary * count
        total_jobs   += count

    market_average = round(total_salary / total_jobs)

    print(f"Market Average Salary: £{market_average}")
    return market_average

get_market_salary("Cloud Engineer", "London")