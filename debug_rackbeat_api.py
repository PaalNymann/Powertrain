#!/usr/bin/env python3
"""
Debug Rackbeat API Response
Check what fields are actually available in Rackbeat products
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

def debug_rackbeat_products():
    """Fetch first few products and show their structure"""
    print("🔍 Debugging Rackbeat API response structure...")
    
    url = f"{RACKBEAT_API}?page=1&limit=5"
    response = requests.get(url, headers=HEADERS, timeout=30)
    
    if response.status_code != 200:
        print(f"❌ API Error: {response.status_code}")
        return
    
    data = response.json()
    products = data.get("products", [])
    
    if not products:
        print("❌ No products found")
        return
    
    print(f"✅ Found {len(products)} products. Analyzing structure...")
    print("=" * 60)
    
    for i, product in enumerate(products[:2]):  # Show first 2 products
        print(f"\n📦 PRODUCT {i+1}:")
        print(f"Name: {product.get('name', 'N/A')}")
        print(f"Number: {product.get('number', 'N/A')}")
        print(f"Group: {product.get('group', {}).get('name', 'N/A')}")
        print(f"Available Quantity: {product.get('available_quantity', 'N/A')}")
        print(f"Sales Price: {product.get('sales_price', 'N/A')}")
        
        # Check for webshop-related fields
        webshop_fields = []
        for key, value in product.items():
            if any(keyword in key.lower() for keyword in ['web', 'shop', 'nett', 'online', 'visible', 'active', 'publish']):
                webshop_fields.append(f"{key}: {value}")
        
        if webshop_fields:
            print("🌐 Webshop-related fields found:")
            for field in webshop_fields:
                print(f"  - {field}")
        else:
            print("❌ No webshop-related fields found")
        
        # Show all available fields
        print("📋 All available fields:")
        for key in sorted(product.keys()):
            value = product[key]
            if isinstance(value, dict):
                print(f"  - {key}: {type(value).__name__} with keys: {list(value.keys())}")
            else:
                print(f"  - {key}: {value}")
        
        print("-" * 40)
    
    # Check for Drivaksel/Mellomaksel products specifically
    print(f"\n🔍 Looking for Drivaksel/Mellomaksel products...")
    
    drive_products = []
    for product in products:
        group_name = product.get("group", {}).get("name", "")
        if group_name in ["Drivaksel", "Mellomaksel"]:
            drive_products.append(product)
    
    if drive_products:
        print(f"✅ Found {len(drive_products)} drive shaft products!")
        for product in drive_products:
            print(f"  - {product.get('name', 'N/A')} (Group: {product.get('group', {}).get('name', 'N/A')})")
    else:
        print("❌ No Drivaksel/Mellomaksel products in first 5 results")
        
        # Show what groups we do have
        groups = set()
        for product in products:
            group_name = product.get("group", {}).get("name", "")
            if group_name:
                groups.add(group_name)
        
        print(f"📊 Product groups found: {sorted(groups)}")

if __name__ == "__main__":
    debug_rackbeat_products()
