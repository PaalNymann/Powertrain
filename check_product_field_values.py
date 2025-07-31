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

def get_product_field_values():
    """Try to get field values for products"""
    try:
        print("🔍 Getting product field values...")
        
        # First get a few products
        response = requests.get(
            f"{RACKBEAT_BASE}/products",
            headers=headers,
            params={"limit": 5},
            timeout=30
        )
        
        if response.status_code in [200, 206]:
            data = response.json()
            products = data.get('products', [])
            
            for i, product in enumerate(products):
                product_id = product.get('id')
                product_name = product.get('name', 'N/A')
                product_number = product.get('number', 'N/A')
                print(f"\n--- Product {i+1}: {product_name} (ID: {product_id}, Number: {product_number}) ---")
                
                if not product_number:
                    print("  ⚠️  No product number found, skipping...")
                    continue
                
                # Try different ways to get field values using product number
                field_endpoints = [
                    f"/products/{product_number}/fields",
                    f"/products/{product_number}/field-values",
                    f"/products/{product_number}/custom-fields",
                    f"/products/{product_number}?include_fields=true"
                ]
                
                for endpoint in field_endpoints:
                    try:
                        field_response = requests.get(
                            f"{RACKBEAT_BASE}{endpoint}",
                            headers=headers,
                            timeout=30
                        )
                        
                        print(f"  {endpoint}: {field_response.status_code}")
                        if field_response.status_code in [200, 206]:
                            field_data = field_response.json()
                            print(f"    ✅ Success! Data: {field_data}")
                            return field_data  # Found working endpoint
                        else:
                            print(f"    ❌ {field_response.text[:100]}...")
                            
                    except Exception as e:
                        print(f"    Error: {e}")
                        
    except Exception as e:
        print(f"Error: {e}")

def try_field_values_endpoint():
    """Try the field-values endpoint directly"""
    try:
        print("\n🔍 Trying /field-values endpoint...")
        response = requests.get(
            f"{RACKBEAT_BASE}/field-values",
            headers=headers,
            params={"limit": 10},
            timeout=30
        )
        
        print(f"Status: {response.status_code}")
        if response.status_code in [200, 206]:
            data = response.json()
            print(f"Response: {data}")
        else:
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"Error: {e}")

def main():
    print("🔍 Finding how to get product field values...")
    
    # Try to get field values for products
    get_product_field_values()
    
    # Try field-values endpoint
    try_field_values_endpoint()

if __name__ == "__main__":
    main() 