#!/usr/bin/env python3
import requests
import os
from dotenv import load_dotenv

load_dotenv()

# Get environment variables
RACKBEAT_API = os.getenv("RACKBEAT_ENDPOINT", "https://app.rackbeat.com/api/products")
RACKBEAT_KEY = os.getenv("RACKBEAT_API_KEY")

print(f"Testing Rackbeat API...")
print(f"Endpoint: {RACKBEAT_API}")
print(f"API Key: {RACKBEAT_KEY[:50]}...")

headers = {
    "Authorization": f"Bearer {RACKBEAT_KEY}",
    "Content-Type": "application/json"
}

try:
    # Test first page
    url = f"{RACKBEAT_API}?page=1&limit=10"
    print(f"\nTesting URL: {url}")
    
    response = requests.get(url, headers=headers, timeout=30)
    print(f"Status Code: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Response keys: {list(data.keys())}")
        if "products" in data:
            print(f"Products count: {len(data['products'])}")
            if data['products']:
                print(f"First product keys: {list(data['products'][0].keys())}")
        if "pages" in data:
            print(f"Total pages: {data['pages']}")
    else:
        print(f"Error response: {response.text[:500]}")
        
except Exception as e:
    print(f"Error: {e}") 