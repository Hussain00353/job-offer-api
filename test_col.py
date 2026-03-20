import http.client
import json

def get_cost_of_living(city, country):
    conn = http.client.HTTPSConnection(
        "cost-of-living-and-prices.p.rapidapi.com"
    )

    headers = {
        'x-rapidapi-key':  "36c39fceccmshff2a1cc9bbf72f5p1ccfa1jsn634879f450de",
        'x-rapidapi-host': "cost-of-living-and-prices.p.rapidapi.com"
    }

    conn.request(
        "GET",
        f"/prices?city_name={city}&country_name={country}",
        headers=headers
    )

    res  = conn.getresponse()
    data = json.loads(res.read().decode("utf-8"))

    # check if we got prices back
    if 'prices' not in data:
        print("Error:", data)
        return 2960  # fallback

    prices = data['prices']

    # extract by good_id (these IDs never change)
    def get_by_id(good_id):
        item = next(
            (p for p in prices if p['good_id'] == good_id), None
        )
        return round(item['avg'], 2) if item else 0

    rent      = get_by_id(29)   # 1 bed city centre
    transport = get_by_id(46)   # monthly pass
    utilities = get_by_id(54)   # electricity + water
    internet  = get_by_id(55)   # internet

    # groceries — realistic monthly estimate for 1 person Dublin
    groceries = round(
        get_by_id(11) * 6  +   # beef 1kg x6
        get_by_id(13) * 6  +   # chicken 1kg x6
        get_by_id(20) * 30 +   # milk 1L x30
        get_by_id(15) * 12 +   # eggs x12
        get_by_id(18) * 16 +   # bread x16
        get_by_id(9)  * 8  +   # apples x8
        get_by_id(25) * 6  +   # rice x6
        get_by_id(26) * 6  +   # tomato x6
        get_by_id(21) * 6  +   # onion x6
        get_by_id(24) * 6  +   # potato x6
        get_by_id(19) * 3  +   # cheese x3
        get_by_id(27) * 20 +   # water x20
        get_by_id(10) * 4  +   # banana x4
        get_by_id(22) * 4  +   # oranges x4
        get_by_id(14) * 8      # beer x8
    , 2)

    # eating out — 3 cheap meals per week
    eating_out = round(get_by_id(38) * 12, 2)

    # entertainment — cinema + gym
    entertainment = round(
        get_by_id(42) * 2  +   # cinema x2
        get_by_id(43)          # gym monthly
    , 2)

    total = round(
        rent + transport + utilities +
        internet + groceries + eating_out + entertainment
    , 2)

    print(f"Rent:           €{rent}")
    print(f"Groceries:      €{groceries}")
    print(f"Eating out:     €{eating_out}")
    print(f"Transport:      €{transport}")
    print(f"Utilities:      €{utilities}")
    print(f"Internet:       €{internet}")
    print(f"Entertainment:  €{entertainment}")
    print(f"────────────────────────────────")
    print(f"Total/month:    €{total}")

    return total

get_cost_of_living("Dublin", "Ireland")