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

def check_fields_endpoint():
    """Check the fields endpoint that was found"""
    try:
        print("🔍 Checking /fields endpoint...")
        response = requests.get(
            f"{RACKBEAT_BASE}/fields",
            headers=headers,
            params={"limit": 20},
            timeout=30
        )
        
        print(f"Status: {response.status_code}")
        if response.status_code in [200, 206]:
            data = response.json()
            print(f"Response keys: {list(data.keys())}")
            
            fields = data.get('fields', [])
            print(f"Found {len(fields)} fields")
            
            # Show the first few fields
            for i, field in enumerate(fields[:10]):
                print(f"\nField {i+1}:")
                print(f"  Name: {field.get('name', 'N/A')}")
                print(f"  Key: {field.get('key', 'N/A')}")
                print(f"  Type: {field.get('type', 'N/A')}")
                print(f"  All keys: {list(field.keys())}")
                
        else:
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"Error: {e}")

def check_products_with_field_relation():
    """Check if we can get products with their field values"""
    try:
        print("\n🔍 Checking if products can be fetched with field values...")
        
        # First get a product ID
        response = requests.get(
            f"{RACKBEAT_BASE}/products",
            headers=headers,
            params={"limit": 1},
            timeout=30
        )
        
        if response.status_code in [200, 206]:
            data = response.json()
            products = data.get('products', [])
            if products:
                product_id = products[0]['id']
                print(f"Using product ID: {product_id}")
                
                # Try to get field values for this product
                field_response = requests.get(
                    f"{RACKBEAT_BASE}/products/{product_id}/fields",
                    headers=headers,
                    timeout=30
                )
                
                print(f"Field values status: {field_response.status_code}")
                if field_response.status_code in [200, 206]:
                    field_data = field_response.json()
                    print(f"Field data: {field_data}")
                else:
                    print(f"Field response: {field_response.text}")
                    
    except Exception as e:
        print(f"Error: {e}")

def main():
    print("🔍 Exploring Rackbeat fields...")
    
    # Check the fields endpoint
    check_fields_endpoint()
    
    # Check if we can get field values for products
    check_products_with_field_relation()

if __name__ == "__main__":
    main() 