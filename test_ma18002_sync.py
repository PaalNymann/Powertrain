#!/usr/bin/env python3
"""
Test script to check MA18002 sync eligibility without API timeouts
"""

import os, requests, json
from dotenv import load_dotenv
load_dotenv()

# Import sync functions
from sync_service import extract_custom_field, filter_keep

RACKBEAT_API = os.getenv("RACKBEAT_ENDPOINT", "https://app.rackbeat.com/api/products")
RACKBEAT_KEY = os.getenv("RACKBEAT_API_KEY")

HEAD_RACK = {
    "Authorization": f"Bearer {RACKBEAT_KEY}",
    "Content-Type": "application/json"
}

def test_ma18002_directly():
    """Test MA18002 sync eligibility directly from Rackbeat"""
    print("🔍 TESTING MA18002 SYNC ELIGIBILITY")
    print("=" * 40)
    
    try:
        # Search for MA18002 in Rackbeat
        params = {
            "limit": 250,
            "page": 1,
            "fields": "number,name,sales_price,available_quantity,group,metadata",
            "search": "MA18002"
        }
        
        print("📡 Fetching MA18002 from Rackbeat...")
        r = requests.get(RACKBEAT_API, headers=HEAD_RACK, params=params, timeout=10)
        
        if r.status_code != 200:
            print(f"❌ Rackbeat API error: {r.status_code}")
            return
            
        data = r.json()
        products = data.get("products", [])
        
        print(f"📦 Found {len(products)} products matching 'MA18002'")
        
        ma18002_found = False
        for product in products:
            number = product.get("number", "")
            if number == "MA18002":
                ma18002_found = True
                print(f"\n✅ FOUND MA18002 in Rackbeat!")
                
                # Check all sync criteria
                print(f"\n🔍 SYNC CRITERIA CHECK:")
                print(f"   Number: {product.get('number', 'N/A')}")
                print(f"   Name: {product.get('name', 'N/A')[:50]}")
                print(f"   Stock: {product.get('available_quantity', 0)}")
                print(f"   Price: {product.get('sales_price', 0)}")
                
                group = product.get("group", {})
                group_name = group.get("name", "N/A")
                print(f"   Group: {group_name}")
                
                # Check metadata fields
                metadata = product.get("metadata", [])
                print(f"\n📋 METADATA FIELDS ({len(metadata)} total):")
                for field in metadata:
                    slug = field.get("slug", "")
                    value = field.get("value", "")
                    print(f"   {slug}: {value}")
                
                # Test i_nettbutikk extraction
                i_nettbutikk = extract_custom_field(product, "i_nettbutikk")
                print(f"\n🔑 CRITICAL FIELD:")
                print(f"   i_nettbutikk: '{i_nettbutikk}'")
                
                # Test sync eligibility
                eligible = filter_keep(product)
                print(f"\n🎯 SYNC RESULT:")
                if eligible:
                    print(f"   ✅ MA18002 SHOULD BE SYNCED!")
                    print(f"   💡 If not in Shopify, sync pipeline has issues")
                else:
                    print(f"   ❌ MA18002 FILTERED OUT!")
                    print(f"   💡 This explains why it's not in Shopify")
                    
                    # Detailed failure analysis
                    print(f"\n🔍 FAILURE ANALYSIS:")
                    if product.get("available_quantity", 0) < 1:
                        print(f"   ❌ Stock too low: {product.get('available_quantity', 0)}")
                    if product.get("sales_price", 0) <= 0:
                        print(f"   ❌ Price too low: {product.get('sales_price', 0)}")
                    if group_name not in ["Drivaksel", "Mellomaksel"]:
                        print(f"   ❌ Wrong group: {group_name}")
                    if i_nettbutikk.lower() != "ja":
                        print(f"   ❌ i_nettbutikk not 'ja': '{i_nettbutikk}'")
                        print(f"   💡 This is likely the main blocker!")
                
                break
        
        if not ma18002_found:
            print(f"\n❌ MA18002 NOT FOUND in Rackbeat!")
            print(f"💡 Product may not exist or search failed")
            
            # Show what we did find
            if products:
                print(f"\n📦 Found these products instead:")
                for p in products[:5]:
                    print(f"   {p.get('number', 'N/A')}: {p.get('name', 'N/A')[:50]}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_ma18002_directly()
