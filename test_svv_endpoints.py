#!/usr/bin/env python3
import requests
import os
from dotenv import load_dotenv

load_dotenv()

# Get environment variables
SVV_API_KEY = os.getenv("SVV_API_KEY")
SVV_ENDPOINT = os.getenv("SVV_ENDPOINT")

print(f"Testing different Statens Vegvesen endpoint variations...")
print(f"Base endpoint: {SVV_ENDPOINT}")
print(f"API Key: {SVV_API_KEY[:20]}...")

# Test different endpoint variations
endpoint_variations = [
    {
        "name": "Original with query param",
        "url": f"{SVV_ENDPOINT}?kjennemerke=KH66644"
    },
    {
        "name": "Path parameter",
        "url": f"{SVV_ENDPOINT}/KH66644"
    },
    {
        "name": "Different base endpoint",
        "url": "https://akfell-datautlevering.atlas.vegvesen.no/enkeltoppslag/kjoretoydata?kjennemerke=KH66644"
    },
    {
        "name": "API v1 endpoint",
        "url": "https://akfell-datautlevering.atlas.vegvesen.no/api/v1/kjoretoydata?kjennemerke=KH66644"
    }
]

headers = {
    "Authorization": f"Bearer {SVV_API_KEY}",
    "Accept": "application/json"
}

for variation in endpoint_variations:
    print(f"\n--- Testing {variation['name']} ---")
    print(f"URL: {variation['url']}")
    try:
        response = requests.get(variation['url'], headers=headers, timeout=30)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("✅ SUCCESS!")
            data = response.json()
            print(f"Response keys: {list(data.keys())}")
            break
        else:
            print(f"Error: {response.text[:200]}")
    except Exception as e:
        print(f"Error: {e}")

# Also test without authentication to see what the API expects
print(f"\n--- Testing without authentication ---")
try:
    response = requests.get(f"{SVV_ENDPOINT}?kjennemerke=KH66644", timeout=30)
    print(f"Status Code: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")
    print(f"Response: {response.text[:500]}")
except Exception as e:
    print(f"Error: {e}") 