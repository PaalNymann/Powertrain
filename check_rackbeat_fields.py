#!/usr/bin/env python3
import requests
import os
from dotenv import load_dotenv

load_dotenv()

RACKBEAT_API_KEY = os.getenv('RACKBEAT_API_KEY')
RACKBEAT_BASE = "https://app.rackbeat.com/api"

headers = {
    "Authorization": f"Bearer {RACKBEAT_API_KEY}",
    "Content-Type": "application/json"
}

def try_different_endpoints():
    """Try different API endpoints to find field data"""
    print("🔍 Trying different Rackbeat API endpoints...")
    
    # Try different endpoints
    endpoints = [
        "/products",
        "/products/fields", 
        "/product-fields",
        "/custom-fields",
        "/fields"
    ]
    
    for endpoint in endpoints:
        try:
            print(f"\n--- Trying endpoint: {endpoint} ---")
            response = requests.get(
                f"{RACKBEAT_BASE}{endpoint}",
                headers=headers,
                params={"limit": 5},
                timeout=30
            )
            
            print(f"Status: {response.status_code}")
            if response.status_code in [200, 206]:
                data = response.json()
                print(f"Response keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                
                # Check if this endpoint has field data
                if 'fields' in data or 'product_fields' in data or 'custom_fields' in data:
                    print("✅ FOUND FIELD DATA!")
                    return data
            else:
                print(f"Response: {response.text[:200]}...")
                
        except Exception as e:
            print(f"Error: {e}")

def fetch_products_with_fields():
    """Try to fetch products with field data included"""
    try:
        print("\n--- Trying products with fields parameter ---")
        response = requests.get(
            f"{RACKBEAT_BASE}/products",
            headers=headers,
            params={"limit": 5, "include_fields": "true", "fields": "true"},
            timeout=30
        )
        
        print(f"Status: {response.status_code}")
        if response.status_code in [200, 206]:
            data = response.json()
            products = data.get("products", [])
            
            for i, product in enumerate(products[:3]):
                print(f"\nProduct {i+1}: {product.get('name', 'N/A')}")
                if 'fields' in product:
                    print("✅ FIELDS FOUND!")
                    for field in product['fields']:
                        print(f"  - {field.get('name', 'N/A')}: {field.get('value', 'N/A')}")
                else:
                    print("No fields found")
                    
    except Exception as e:
        print(f"Error: {e}")

def main():
    print("🔍 Checking Rackbeat field access methods...")
    
    # Try different endpoints
    try_different_endpoints()
    
    # Try products with field parameters
    fetch_products_with_fields()

if __name__ == "__main__":
    main() 