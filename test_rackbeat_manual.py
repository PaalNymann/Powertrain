#!/usr/bin/env python3
import requests
import os
from dotenv import load_dotenv

load_dotenv()

def test_rackbeat_manual():
    """Manual test for Rackbeat API - modify with working details from Sintra"""
    
    print("=== MANUAL RACKBEAT API TEST ===")
    print("Modify this script with the exact working API details from Sintra")
    
    # MODIFY THESE VALUES WITH THE WORKING SINTRA CONFIGURATION
    RACKBEAT_API_KEY = os.getenv('RACKBEAT_API_KEY')  # Replace if different
    RACKBEAT_ENDPOINT = os.getenv('RACKBEAT_ENDPOINT')  # Replace if different
    
    print(f"Current endpoint: {RACKBEAT_ENDPOINT}")
    print(f"Current API key: {RACKBEAT_API_KEY[:50]}...")
    
    # MODIFY THESE HEADERS IF DIFFERENT FROM SINTRA
    headers = {
        "Authorization": f"Bearer {RACKBEAT_API_KEY}",
        "Content-Type": "application/json"
        # Add any additional headers that were working in Sintra
    }
    
    # MODIFY THIS URL IF DIFFERENT FROM SINTRA
    url = f"{RACKBEAT_ENDPOINT}?page[size]=10"
    
    print(f"\nTesting URL: {url}")
    print(f"Headers: {headers}")
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✓ SUCCESS!")
            print(f"Response keys: {list(data.keys())}")
            
            products = data.get("data", [])
            print(f"Products found: {len(products)}")
            
            if products:
                first_product = products[0]
                print(f"First product structure: {list(first_product.keys())}")
                
                attrs = first_product.get("attributes", {})
                print(f"Attributes: {list(attrs.keys())}")
            
            return True
        else:
            print(f"✗ Error: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ Exception: {e}")
        return False

if __name__ == "__main__":
    print("Instructions:")
    print("1. Replace RACKBEAT_API_KEY with the exact key from Sintra")
    print("2. Replace RACKBEAT_ENDPOINT with the exact endpoint from Sintra") 
    print("3. Add any additional headers that were required in Sintra")
    print("4. Run this script to test")
    print()
    
    success = test_rackbeat_manual()
    if success:
        print("\n✓ API is working! Use these exact settings in the sync service.")
    else:
        print("\n✗ Still not working. Check the Sintra configuration.") 