#!/usr/bin/env python3
"""
Check detailed product endpoint for custom fields
"""

import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

RACKBEAT_API = os.getenv("RACKBEAT_ENDPOINT", "https://app.rackbeat.com/api/products")
RACKBEAT_KEY = os.getenv("RACKBEAT_API_KEY")

HEADERS = {
    "Authorization": f"Bearer {RACKBEAT_KEY}",
    "Content-Type": "application/json"
}

def check_product_details():
    print("🔍 CHECKING PRODUCT DETAILS ENDPOINT")
    print("=" * 40)
    
    # First get a product SKU
    url = f"{RACKBEAT_API}?page=1&limit=1"
    response = requests.get(url, headers=HEADERS, timeout=30)
    
    if response.status_code not in [200, 206]:
        print(f"❌ Error: {response.status_code}")
        return
    
    data = response.json()
    products = data["products"]
    
    if not products:
        print("❌ No products found")
        return
    
    product = products[0]
    sku = product["number"]
    
    print(f"📋 Checking details for SKU: {sku}")
    
    # Try different endpoints
    endpoints = [
        f"{RACKBEAT_API}/{sku}",
        f"{RACKBEAT_API}/{sku}/details",
        f"{RACKBEAT_API}/{sku}/fields",
        f"{RACKBEAT_API}/{sku}/custom-fields",
        f"{RACKBEAT_API}/{sku}/metafields",
    ]
    
    for endpoint in endpoints:
        print(f"\n🔍 Trying: {endpoint}")
        try:
            response = requests.get(endpoint, headers=HEADERS, timeout=30)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print("✅ Success! Found data:")
                
                # Look for custom fields
                if isinstance(data, dict):
                    for key, value in data.items():
                        if 'field' in key.lower() or 'custom' in key.lower() or 'meta' in key.lower():
                            print(f"  🔍 {key}: {value}")
                
                # Also check if there are any nested objects with field-like names
                for key, value in data.items():
                    if isinstance(value, dict):
                        field_keys = [k for k in value.keys() if 'field' in k.lower() or 'number' in k.lower()]
                        if field_keys:
                            print(f"  📁 {key}: {field_keys}")
                
                break
            else:
                print(f"❌ Not found")
                
        except Exception as e:
            print(f"❌ Error: {e}")
    
    # Also check if there are any field-related endpoints
    print(f"\n🔍 CHECKING FIELD-RELATED ENDPOINTS:")
    print("-" * 40)
    
    field_endpoints = [
        f"{RACKBEAT_API.replace('/products', '/fields')}",
        f"{RACKBEAT_API.replace('/products', '/custom-fields')}",
        f"{RACKBEAT_API.replace('/products', '/metafields')}",
    ]
    
    for endpoint in field_endpoints:
        print(f"\n🔍 Trying: {endpoint}")
        try:
            response = requests.get(endpoint, headers=HEADERS, timeout=30)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print("✅ Found field configuration!")
                print(json.dumps(data, indent=2)[:500] + "...")
                break
                
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    check_product_details() 