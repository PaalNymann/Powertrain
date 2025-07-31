#!/usr/bin/env python3
import requests
import os
from dotenv import load_dotenv

load_dotenv()

# Get environment variables
SVV_API_KEY = os.getenv("SVV_API_KEY")
SVV_ENDPOINT = os.getenv("SVV_ENDPOINT")
BUYPASS_CERT_PATH = os.getenv("BUYPASS_CERT_PATH")
BUYPASS_CERT_PASSWORD = os.getenv("BUYPASS_CERT_PASSWORD")
CLIENT_ID = os.getenv("CLIENT_ID")
SCOPE = os.getenv("SCOPE")

print(f"Testing Statens Vegvesen API with different auth methods...")
print(f"Endpoint: {SVV_ENDPOINT}")
print(f"API Key: {SVV_API_KEY[:20]}...")
print(f"Client ID: {CLIENT_ID}")

# Test different authentication methods
auth_methods = [
    {
        "name": "Bearer Token",
        "headers": {
            "Authorization": f"Bearer {SVV_API_KEY}",
            "Accept": "application/json"
        }
    },
    {
        "name": "SVV-Api-Key",
        "headers": {
            "SVV-Api-Key": SVV_API_KEY,
            "Accept": "application/json"
        }
    },
    {
        "name": "X-API-Key",
        "headers": {
            "X-API-Key": SVV_API_KEY,
            "Accept": "application/json"
        }
    },
    {
        "name": "Client ID Header",
        "headers": {
            "Authorization": f"Bearer {SVV_API_KEY}",
            "X-Client-ID": CLIENT_ID,
            "Accept": "application/json"
        }
    }
]

regnr = "KH66644"
url = f"{SVV_ENDPOINT}?kjennemerke={regnr}"

for method in auth_methods:
    print(f"\n--- Testing {method['name']} ---")
    try:
        response = requests.get(url, headers=method['headers'], timeout=30)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("✅ SUCCESS!")
            data = response.json()
            print(f"Response keys: {list(data.keys())}")
            break
        else:
            print(f"Headers: {dict(response.headers)}")
            print(f"Error: {response.text[:200]}")
    except Exception as e:
        print(f"Error: {e}")

print(f"\n--- Testing with certificate path ---")
print(f"Certificate path: {BUYPASS_CERT_PATH}")
print(f"Certificate exists: {os.path.exists(BUYPASS_CERT_PATH) if BUYPASS_CERT_PATH else 'Not specified'}") 