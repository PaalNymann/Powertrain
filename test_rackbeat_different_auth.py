#!/usr/bin/env python3
import requests
import os
from dotenv import load_dotenv

load_dotenv()

def test_rackbeat_different_auth():
    """Test Rackbeat API with different authentication methods"""
    
    print("=== RACKBEAT API AUTHENTICATION TEST ===")
    
    RACKBEAT_API_KEY = os.getenv('RACKBEAT_API_KEY')
    RACKBEAT_ENDPOINT = os.getenv('RACKBEAT_ENDPOINT')
    
    print(f"Endpoint: {RACKBEAT_ENDPOINT}")
    print(f"API Key: {RACKBEAT_API_KEY[:50]}...")
    
    # Test different authentication methods
    auth_methods = [
        {
            'name': 'Bearer Token',
            'headers': {
                'Authorization': f'Bearer {RACKBEAT_API_KEY}',
                'Content-Type': 'application/json'
            }
        },
        {
            'name': 'API Key Header',
            'headers': {
                'X-API-Key': RACKBEAT_API_KEY,
                'Content-Type': 'application/json'
            }
        },
        {
            'name': 'Authorization Header (no Bearer)',
            'headers': {
                'Authorization': RACKBEAT_API_KEY,
                'Content-Type': 'application/json'
            }
        },
        {
            'name': 'Rackbeat API Key Header',
            'headers': {
                'Rackbeat-API-Key': RACKBEAT_API_KEY,
                'Content-Type': 'application/json'
            }
        }
    ]
    
    for method in auth_methods:
        print(f"\n--- Testing {method['name']} ---")
        try:
            response = requests.get(
                f"{RACKBEAT_ENDPOINT}?page=1&limit=5",
                headers=method['headers'],
                timeout=15
            )
            
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✓ SUCCESS with {method['name']}!")
                print(f"Total products: {data.get('meta', {}).get('total', 'Unknown')}")
                return method['headers']  # Return the working method
            else:
                print(f"Response: {response.text[:100]}...")
                
        except requests.exceptions.Timeout:
            print("Timeout")
        except Exception as e:
            print(f"Error: {e}")
    
    print("\n✗ None of the authentication methods worked")
    return None

if __name__ == "__main__":
    working_auth = test_rackbeat_different_auth()
    if working_auth:
        print(f"\n✓ Use this authentication method: {working_auth}") 