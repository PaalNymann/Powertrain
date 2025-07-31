#!/usr/bin/env python3
"""
Simple test to check field value fetching
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

def test_single_product():
    print("🧪 TESTING SINGLE PRODUCT FIELD FETCHING")
    print("=" * 45)
    
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
    name = product["name"]
    
    print(f"📋 Testing product: {name}")
    print(f"SKU: {sku}")
    
    # Test field value fetching
    try:
        field_url = f"{RACKBEAT_API}/{sku}"
        field_response = requests.get(field_url, headers=HEADERS, timeout=30)
        
        print(f"Field API status: {field_response.status_code}")
        
        if field_response.status_code == 200:
            field_data = field_response.json()
            print("✅ Field data retrieved successfully")
            
            # Check if field_values exists
            if 'product' in field_data and 'field_values' in field_data['product']:
                print(f"📝 Found {len(field_data['product']['field_values'])} field values")
                
                field_values = {}
                for field_value in field_data['product']['field_values']:
                    field_slug = field_value['field']['slug']
                    value = field_value.get('value', '')
                    field_values[field_slug] = value
                    print(f"  🔍 {field_slug}: {value}")
                
                # Test metafield mapping
                metafields = {
                    "number":                product.get("number", ""),
                    "original_nummer":       field_values.get("original-nummer", ""),
                    "tirsan_varenummer":     field_values.get("tirsan-varenummer", ""),
                    "odm_varenummer":        field_values.get("odm-varenummer", ""),
                    "ims_varenummer":        field_values.get("ims-varenummer", ""),
                    "welte_varenummer":      field_values.get("welte-varenummer", ""),
                    "bakkeren_varenummer":   field_values.get("bakkeren-varenummer", ""),
                }
                
                print("\n🏷️  Metafield mapping:")
                for key, value in metafields.items():
                    if value:
                        print(f"  ✅ {key}: {value}")
                    else:
                        print(f"  ❌ {key}: (empty)")
            else:
                print("❌ No field_values found in response")
                print("Available keys:", list(field_data.keys()))
        else:
            print(f"❌ Error: {field_response.text}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    test_single_product() 