import json
import boto3
import os

# ── AWS client to call Lambda 2 ──────────────────────────
lambda_client = boto3.client('lambda')

# ── Helper: affordability score ──────────────────────────
def calculate_score(monthly_savings, monthly_income, salary_vs_market=0):
    if monthly_income <= 0:
        return 0
    if monthly_savings <= 0:
        return 0

    # affordability component (0-70 points)
    affordability = min(70, round((monthly_savings / monthly_income) * 140))

    # market position component (0-30 points)
    if salary_vs_market >= 0:
        market_score = 30
    elif salary_vs_market >= -5000:
        market_score = 20
    elif salary_vs_market >= -10000:
        market_score = 10
    elif salary_vs_market >= -20000:
        market_score = 5
    else:
        market_score = 0

    return min(100, affordability + market_score)

# ── Helper: recommendation ────────────────────────────────
def get_recommendation(score):
    if score >= 75:
        return "Excellent Offer"
    elif score >= 55:
        return "Good Offer"
    elif score >= 40:
        return "Fair Offer - Try to Negotiate"
    else:
        return "Poor Offer - Consider Declining"

# ── Helper: calculate Irish net monthly salary (2026) ────
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

# ── Lambda 1 handler ─────────────────────────────────────
def lambda_handler(event, context):
    try:
        # Step 1 — parse input (SQS or direct)
        if 'Records' in event:
            body = json.loads(event['Records'][0]['body'])
        else:
            if 'body' in event:
                body = json.loads(event['body'])
            else:
                body = event

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
                'job_title':           job_title,
                'city':                city,
                'country':             country,
                'gross_annual_salary': salary,
            })
        )

        # Step 4 — read Lambda 2 response
        lambda2_data  = json.loads(
            lambda2_response['Payload'].read()
        )
        salary_data   = lambda2_data.get('salary_data')
        market_salary = salary_data['median_salary'] if salary_data else 0
        salary_source = salary_data['salary_source'] if salary_data else 'N/A'
        monthly_cost  = lambda2_data.get('monthly_cost', 2960)
        cost_source   = lambda2_data.get('cost_source', 'N/A')
        tax_breakdown = lambda2_data.get('tax_breakdown', {})

        # Step 5 — do all calculations
        monthly_income   = tax_breakdown.get('net_monthly', round(salary / 12))
        salary_vs_market = salary - market_salary
        monthly_savings  = round(monthly_income - monthly_cost)
        score            = calculate_score(monthly_savings, monthly_income, salary_vs_market)
        recommendation   = get_recommendation(score)

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
                'recommendation':            recommendation,
                'salary_source':             salary_source,
                'cost_source':               cost_source,
                'tax_breakdown':             tax_breakdown,
            })
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }
