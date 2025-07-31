#!/usr/bin/env python3
"""
Debug product data structure
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

def debug_product():
    print("🔍 DEBUGGING PRODUCT DATA STRUCTURE")
    print("=" * 40)
    
    # Get one product
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
    
    # Get detailed product data
    field_url = f"{RACKBEAT_API}/{sku}"
    field_response = requests.get(field_url, headers=HEADERS, timeout=30)
    
    if field_response.status_code == 200:
        field_data = field_response.json()
        print("✅ Product data retrieved")
        
        # Show the structure
        print("\n📁 Data structure:")
        print(json.dumps(field_data, indent=2)[:1000] + "...")
        
        # Check product keys
        if 'product' in field_data:
            product_data = field_data['product']
            print(f"\n📁 Product keys: {list(product_data.keys())}")
            
            # Check if field_values exists in product
            if 'field_values' in product_data:
                print(f"✅ Found {len(product_data['field_values'])} field values")
                for field_value in product_data['field_values']:
                    field_slug = field_value['field']['slug']
                    value = field_value.get('value', '')
                    print(f"  📝 {field_slug}: {value}")
            else:
                print("❌ No field_values in product data")
        else:
            print("❌ No 'product' key found")
    else:
        print(f"❌ Error: {field_response.status_code}")

if __name__ == "__main__":
    debug_product() 