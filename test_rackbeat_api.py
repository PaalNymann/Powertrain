#!/usr/bin/env python3
import requests
import os
from dotenv import load_dotenv

load_dotenv()

def test_rackbeat_api():
    """Test Rackbeat API connectivity"""
    
    print("=== RACKBEAT API TEST ===")
    
    RACKBEAT_API_KEY = os.getenv('RACKBEAT_API_KEY')
    RACKBEAT_ENDPOINT = os.getenv('RACKBEAT_ENDPOINT')
    
    print(f"Endpoint: {RACKBEAT_ENDPOINT}")
    print(f"API Key: {RACKBEAT_API_KEY[:50]}...")
    
    try:
        headers = {
            'Authorization': f'Bearer {RACKBEAT_API_KEY}',
            'Content-Type': 'application/json'
        }
        
        print("\nTesting Rackbeat API call...")
        print("(This may take a few seconds)")
        
        response = requests.get(
            f"{RACKBEAT_ENDPOINT}?page=1&limit=10",
            headers=headers,
            timeout=30
        )
        
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✓ Rackbeat API is working!")
            print(f"Total products: {data.get('meta', {}).get('total', 'Unknown')}")
            print(f"Products in first page: {len(data.get('data', []))}")
        else:
            print(f"✗ API error: {response.status_code}")
            print(f"Response: {response.text[:200]}...")
            
    except requests.exceptions.Timeout:
        print("✗ Request timed out - API might be slow or unreachable")
    except requests.exceptions.RequestException as e:
        print(f"✗ Request error: {e}")
    except Exception as e:
        print(f"✗ Error: {e}")

if __name__ == "__main__":
    test_rackbeat_api() 