#!/usr/bin/env python3
import requests
import os
from dotenv import load_dotenv

load_dotenv()

RACKBEAT_API_KEY = os.getenv('RACKBEAT_API_KEY')
RACKBEAT_API = "https://app.rackbeat.com/api/products"

headers = {
    "Authorization": f"Bearer {RACKBEAT_API_KEY}",
    "Content-Type": "application/json"
}

def fetch_individual_product(sku):
    """Fetch a single product by SKU to see if it has fields"""
    try:
        response = requests.get(
            f"{RACKBEAT_API}/{sku}",
            headers=headers,
            timeout=30
        )
        
        if response.status_code in [200, 206]:
            data = response.json()
            product = data.get('product', data)  # Handle both direct and nested responses
            print(f"✅ Fetched individual product: {sku}")
            return product
        else:
            print(f"❌ Failed to fetch product {sku}: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Exception fetching product {sku}: {e}")
        return None

def main():
    print("🔍 Checking individual Rackbeat products for fields...")
    
    # Try a few different SKUs
    test_skus = ["MA01032-Kryssvariant", "MA01006-kryssvariant", "MA01004-Kryssvariant"]
    
    for sku in test_skus:
        print(f"\n--- Checking product: {sku} ---")
        product = fetch_individual_product(sku)
        
        if product:
            print(f"Name: {product.get('name', 'N/A')}")
            print(f"Number: {product.get('number', 'N/A')}")
            
            # Check for fields
            if 'fields' in product:
                print("Fields found:")
                for field in product['fields']:
                    print(f"  - {field.get('name', 'N/A')}: {field.get('value', 'N/A')}")
            else:
                print("No 'fields' found in product")
            
            # Check for field_values
            if 'field_values' in product:
                print("Field values found:")
                for key, value in product['field_values'].items():
                    print(f"  - {key}: {value}")
            else:
                print("No 'field_values' found in product")
            
            # Check all keys
            print("All product keys:")
            for key in product.keys():
                print(f"  - {key}")

if __name__ == "__main__":
    main() 