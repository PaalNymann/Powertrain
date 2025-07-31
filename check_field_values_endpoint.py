#!/usr/bin/env python3
"""
Check field values endpoint for specific product
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

def check_field_values():
    print("🔍 CHECKING FIELD VALUES ENDPOINT")
    print("=" * 35)
    
    # Get a product SKU
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
    
    print(f"📋 Product SKU: {sku}")
    
    # Try different field value endpoints
    endpoints = [
        f"{RACKBEAT_API.replace('/products', '/field-values')}?item={sku}",
        f"{RACKBEAT_API.replace('/products', '/field-values')}?product={sku}",
        f"{RACKBEAT_API.replace('/products', '/field-values')}?number={sku}",
        f"{RACKBEAT_API}/{sku}/field-values",
        f"{RACKBEAT_API.replace('/products', '/field-values')}",
    ]
    
    for endpoint in endpoints:
        print(f"\n🔍 Trying: {endpoint}")
        try:
            response = requests.get(endpoint, headers=HEADERS, timeout=30)
            print(f"Status: {response.status_code}")
            
            if response.status_code in [200, 206]:
                data = response.json()
                print("✅ Success!")
                
                # Look for field values for this specific product
                if 'field_values' in data:
                    field_values = data['field_values']
                    print(f"📝 Found {len(field_values)} total field values")
                    
                    # Filter for this specific product
                    product_field_values = []
                    for field_value in field_values:
                        if 'item' in field_value and field_value['item'] == sku:
                            product_field_values.append(field_value)
                        elif 'product' in field_value and field_value['product'] == sku:
                            product_field_values.append(field_value)
                    
                    if product_field_values:
                        print(f"✅ Found {len(product_field_values)} field values for this product:")
                        for field_value in product_field_values:
                            field_slug = field_value['field']['slug']
                            value = field_value.get('value', '')
                            print(f"  📝 {field_slug}: {value}")
                        break
                    else:
                        print("❌ No field values found for this specific product")
                else:
                    print("❌ No field_values in response")
            else:
                print(f"❌ Not found")
                
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    check_field_values() 