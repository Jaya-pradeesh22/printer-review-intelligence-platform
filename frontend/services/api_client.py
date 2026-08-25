import requests

BASE_URL = "http://127.0.0.1:8000"

def get_analytics():

    response = requests.get(
        
        f"{BASE_URL}/analytics"
    )

    return response.json()