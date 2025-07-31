#!/usr/bin/env python3
import requests
import os
from dotenv import load_dotenv

load_dotenv()

# Get environment variables
SVV_API_KEY = os.getenv("SVV_API_KEY")
SVV_ENDPOINT = os.getenv("SVV_ENDPOINT")

print(f"Testing Statens Vegvesen API with SVV-Authorization...")
print(f"Endpoint: {SVV_ENDPOINT}")
print(f"API Key: {SVV_API_KEY[:20]}...")

headers = {
    "SVV-Authorization": SVV_API_KEY,
    "Accept": "application/json"
}

try:
    # Test with license plate
    regnr = "KH66644"
    url = f"{SVV_ENDPOINT}?kjennemerke={regnr}"
    print(f"\nTesting URL: {url}")
    print(f"Headers: {headers}")
    
    response = requests.get(url, headers=headers, timeout=30)
    print(f"Status Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    
    if response.status_code == 200:
        print("✅ SUCCESS!")
        data = response.json()
        print(f"Response keys: {list(data.keys())}")
        if "kjoretoydataListe" in data:
            print(f"Vehicle data count: {len(data['kjoretoydataListe'])}")
    else:
        print(f"Error response: {response.text[:500]}")
        
except Exception as e:
    print(f"Error: {e}") 