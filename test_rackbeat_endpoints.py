#!/usr/bin/env python3
import requests
import os
from dotenv import load_dotenv

load_dotenv()

def test_rackbeat_endpoints():
    """Test different Rackbeat API endpoints"""
    
    print("=== RACKBEAT API ENDPOINT TEST ===")
    
    RACKBEAT_API_KEY = os.getenv('RACKBEAT_API_KEY')
    BASE_URL = "https://app.rackbeat.com/api"
    
    print(f"API Key: {RACKBEAT_API_KEY[:50]}...")
    
    # Test different endpoints
    endpoints = [
        "/products",
        "/products/",
        "/v1/products",
        "/v2/products", 
        "/products.json",
        "/",
        "/health",
        "/status"
    ]
    
    headers = {
        'Authorization': f'Bearer {RACKBEAT_API_KEY}',
        'Content-Type': 'application/json'
    }
    
    for endpoint in endpoints:
        print(f"\n--- Testing {endpoint} ---")
        try:
            url = f"{BASE_URL}{endpoint}"
            print(f"URL: {url}")
            
            response = requests.get(
                url,
                headers=headers,
                timeout=10
            )
            
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                print(f"✓ SUCCESS with {endpoint}!")
                try:
                    data = response.json()
                    print(f"Response keys: {list(data.keys()) if isinstance(data, dict) else 'Not JSON'}")
                except:
                    print("Response is not JSON")
                return endpoint
            elif response.status_code == 404:
                print("Endpoint not found")
            else:
                print(f"Response: {response.text[:100]}...")
                
        except requests.exceptions.Timeout:
            print("Timeout")
        except Exception as e:
            print(f"Error: {e}")
    
    print("\n✗ None of the endpoints worked")
    return None

if __name__ == "__main__":
    working_endpoint = test_rackbeat_endpoints()
    if working_endpoint:
        print(f"\n✓ Use this endpoint: {working_endpoint}") 