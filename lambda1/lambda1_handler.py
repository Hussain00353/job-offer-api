import json
import boto3
import os

# ── AWS client to call Lambda 2 ──────────────────────────
lambda_client = boto3.client('lambda')

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

# ── Lambda 1 handler ─────────────────────────────────────
def lambda_handler(event, context):
    try:

        # Step 1 — parse input from SQS message
        body      = json.loads(event['Records'][0]['body'])
        job_title = body.get('job_title')
        city      = body.get('city')
        salary    = body.get('gross_annual_salary')
        country   = body.get('country', 'Ireland')

        # Step 2 — validate inputs
        if not job_title or not city or not salary:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Missing required fields: job_title, city, gross_annual_salary'
                })
            }

        # Step 3 — call Lambda 2 to get external data
        lambda2_response = lambda_client.invoke(
            FunctionName   = os.environ.get('LAMBDA2_FUNCTION_NAME'),
            InvocationType = 'RequestResponse',
            Payload        = json.dumps({
                'job_title': job_title,
                'city':      city,
                'country':   country
            })
        )

        # Step 4 — read Lambda 2 response
        lambda2_data  = json.loads(
            lambda2_response['Payload'].read()
        )
        salary_data   = lambda2_data.get('salary_data')
        market_salary = salary_data['median_salary'] if salary_data else 0
        monthly_cost  = lambda2_data.get('monthly_cost', 2960)

        # Step 5 — do all calculations
        salary_vs_market = salary - market_salary
        monthly_income   = round(salary / 12)
        monthly_savings  = round(monthly_income - monthly_cost)
        score            = calculate_score(monthly_savings, monthly_income)
        recommendation   = get_recommendation(score, salary_vs_market)

        # Step 6 — return final response
        return {
            'statusCode': 200,
            'body': json.dumps({
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
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }