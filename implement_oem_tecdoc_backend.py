#!/usr/bin/env python3
"""
Implement OEM-based TecDoc search in backend for ZT41818 and similar vehicles
This replaces the previous vehicle-id approach with direct OEM search
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import requests
import json
from typing import List, Dict, Set

# Backend configuration
BACKEND_URL = "https://web-production-0809b.up.railway.app"

def test_oem_based_search_for_zt41818():
    """Test OEM-based TecDoc search for ZT41818 via backend"""
    
    print("🔍 TESTING OEM-BASED TECDOC SEARCH FOR ZT41818")
    print("=" * 60)
    
    # Test the backend search endpoint with ZT41818
    license_plate = "ZT41818"
    
    print(f"📋 Testing backend search for license plate: {license_plate}")
    
    # Test POST endpoint (used by webshop)
    search_url = f"{BACKEND_URL}/api/car_parts_search"
    payload = {"license_plate": license_plate}
    
    try:
        print(f"🔍 Sending POST request to: {search_url}")
        print(f"📋 Payload: {payload}")
        
        response = requests.post(search_url, json=payload, timeout=30)
        
        print(f"📊 Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"✅ Backend search successful!")
            print(f"📊 Response structure: {type(data)}")
            
            if isinstance(data, dict):
                print(f"📋 Response keys: {list(data.keys())}")
                
                # Check for products
                products = data.get('products', [])
                if products:
                    print(f"🎯 Found {len(products)} products!")
                    
                    # Analyze the products
                    for i, product in enumerate(products[:5]):  # Show first 5
                        product_id = product.get('id', 'N/A')
                        title = product.get('title', 'N/A')
                        handle = product.get('handle', 'N/A')
                        
                        print(f"   {i+1}. {title} (ID: {product_id}, Handle: {handle})")
                        
                        # Check for OEM numbers in metafields
                        metafields = product.get('metafields', {})
                        original_nummer = metafields.get('Original_nummer', 'N/A')
                        product_group = metafields.get('product_group', 'N/A')
                        
                        print(f"      Group: {product_group}")
                        print(f"      OEM: {original_nummer}")
                        
                        # Check if this is MA18002
                        if 'MA18002' in handle or 'MA18002' in title:
                            print(f"      🎯 FOUND MA18002!")
                    
                    if len(products) > 5:
                        print(f"   ... and {len(products) - 5} more products")
                        
                        # Check if MA18002 is in the remaining products
                        ma18002_found = False
                        for product in products[5:]:
                            handle = product.get('handle', '')
                            title = product.get('title', '')
                            if 'MA18002' in handle or 'MA18002' in title:
                                print(f"   🎯 FOUND MA18002 in remaining products!")
                                ma18002_found = True
                                break
                        
                        if not ma18002_found:
                            print(f"   ⚠️ MA18002 not found in search results")
                else:
                    print(f"❌ No products found in response")
                    
                # Check for any error messages or debug info
                error = data.get('error')
                if error:
                    print(f"❌ Backend error: {error}")
                    
                debug_info = data.get('debug_info', {})
                if debug_info:
                    print(f"🔍 Debug info: {debug_info}")
                    
            elif isinstance(data, list):
                print(f"📊 Response is a list with {len(data)} items")
                if data:
                    print(f"📋 Sample item: {data[0]}")
            else:
                print(f"⚠️ Unexpected response format: {type(data)}")
                print(f"📋 Response: {data}")
                
        else:
            print(f"❌ Backend search failed: {response.status_code}")
            print(f"📋 Response text: {response.text}")
            
    except Exception as e:
        print(f"❌ Exception during backend search: {e}")

def compare_with_direct_tecdoc():
    """Compare backend results with direct TecDoc OEM search"""
    
    print(f"\n🔍 COMPARING WITH DIRECT TECDOC OEM SEARCH")
    print("=" * 50)
    
    # Known Nissan X-Trail OEMs
    target_oems = ["370008H310", "370008H510", "370008H800"]
    
    print(f"📋 Direct TecDoc search found 18 articles with 103 unique OEMs")
    print(f"📋 Key OEMs include: {', '.join(target_oems)}")
    print(f"📋 Additional OEMs include: 37000-8H310, 37000-8H510, 37000-8H800, etc.")
    
    print(f"\n💡 Expected backend behavior:")
    print(f"1. Backend should use OEM-based TecDoc search for ZT41818")
    print(f"2. Should collect all 103 OEMs from TecDoc articles")
    print(f"3. Should match these OEMs against Shopify products")
    print(f"4. Should return products where Original_nummer contains any matching OEM")
    print(f"5. MA18002 should appear if it has matching OEMs in its Original_nummer field")

def test_ma18002_sync_status():
    """Test if MA18002 is properly synced to Shopify"""
    
    print(f"\n🔍 TESTING MA18002 SYNC STATUS")
    print("=" * 40)
    
    # Test the diagnostic endpoint we created earlier
    test_url = f"{BACKEND_URL}/test/ma18002"
    
    try:
        print(f"🔍 Checking MA18002 sync status: {test_url}")
        
        response = requests.get(test_url, timeout=15)
        
        print(f"📊 Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ MA18002 diagnostic successful!")
            print(f"📋 Response: {json.dumps(data, indent=2)}")
        else:
            print(f"❌ MA18002 diagnostic failed: {response.status_code}")
            print(f"📋 Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Exception during MA18002 diagnostic: {e}")

if __name__ == "__main__":
    # Test 1: Backend search for ZT41818
    test_oem_based_search_for_zt41818()
    
    # Test 2: Compare with direct TecDoc results
    compare_with_direct_tecdoc()
    
    # Test 3: Check MA18002 sync status
    test_ma18002_sync_status()
    
    print(f"\n🎯 CONCLUSION:")
    print(f"If backend search now returns compatible products for ZT41818:")
    print(f"✅ OEM-based TecDoc integration is working correctly")
    print(f"✅ The TecDoc VIN OEM matching issue is resolved")
    print(f"💡 If MA18002 still doesn't appear, the issue is in product sync, not TecDoc")
    print(f"💡 If no products appear, the OEM matching logic needs debugging")
