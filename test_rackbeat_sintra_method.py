#!/usr/bin/env python3
import requests
import os
from dotenv import load_dotenv

load_dotenv()

def test_rackbeat_sintra_method():
    """Test Rackbeat API using Sintra's working method"""
    
    print("=== RACKBEAT API SINTRA METHOD TEST ===")
    
    RACKBEAT_API_KEY = os.getenv('RACKBEAT_API_KEY')
    RACKBEAT_ENDPOINT = os.getenv('RACKBEAT_ENDPOINT')
    
    print(f"Endpoint: {RACKBEAT_ENDPOINT}")
    print(f"API Key: {RACKBEAT_API_KEY[:50]}...")
    
    try:
        # Use Sintra's working method
        url = f"{RACKBEAT_ENDPOINT}?page[size]=10"
        headers = {"Authorization": f"Bearer {RACKBEAT_API_KEY}"}
        
        print(f"\nTesting URL: {url}")
        print("(This may take a few seconds)")
        
        response = requests.get(url, headers=headers, timeout=30)
        
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✓ SUCCESS with Sintra method!")
            
            # Check the structure
            products = data.get("data", [])
            print(f"Products found: {len(products)}")
            
            if products:
                first_product = products[0]
                attrs = first_product.get("attributes", {})
                print(f"First product name: {attrs.get('name', 'N/A')}")
                print(f"First product price: {attrs.get('sales_price', 'N/A')}")
                print(f"First product available: {attrs.get('available', 'N/A')}")
            
            # Check pagination
            next_url = data.get("links", {}).get("next")
            print(f"Next page URL: {next_url}")
            
            return True
        else:
            print(f"✗ API error: {response.status_code}")
            print(f"Response: {response.text[:200]}...")
            return False
            
    except requests.exceptions.Timeout:
        print("✗ Request timed out")
        return False
    except requests.exceptions.RequestException as e:
        print(f"✗ Request error: {e}")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_rackbeat_sintra_method()
    if success:
        print("\n✓ Sintra method works! The sync service should work now.")
    else:
        print("\n✗ Sintra method failed. Need to investigate further.") 