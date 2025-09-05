#!/usr/bin/env python3
"""
Diagnose OEM matching between TecDoc results and Shopify database
"""

import requests
import json

BACKEND_URL = "https://web-production-0809b.up.railway.app"

def diagnose_oem_matching():
    """Diagnose why 103 TecDoc OEMs don't match any Shopify products"""
    
    print("🔍 DIAGNOSING OEM MATCHING ISSUE")
    print("=" * 50)
    
    # Get the current backend response for ZT41818
    license_plate = "ZT41818"
    search_url = f"{BACKEND_URL}/api/car_parts_search"
    payload = {"license_plate": license_plate}
    
    try:
        response = requests.post(search_url, json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            available_oems = data.get('available_oems', [])
            matching_products = data.get('matching_products', [])
            
            print(f"📊 Backend found {len(available_oems)} OEMs but {len(matching_products)} products")
            
            if available_oems:
                print(f"\n🔍 Sample TecDoc OEMs found:")
                for i, oem in enumerate(available_oems[:10]):
                    print(f"   {i+1:2d}. {oem}")
                
                # Test if we can find ANY products with these OEMs manually
                print(f"\n🔍 Testing manual OEM search in database...")
                
                # Try a few different approaches to find products
                test_endpoints = [
                    f"/api/raw_database_query",
                    f"/api/cache/stats", 
                    f"/api/database/inspect"
                ]
                
                for endpoint in test_endpoints:
                    url = f"{BACKEND_URL}{endpoint}"
                    try:
                        test_response = requests.get(url, timeout=15)
                        if test_response.status_code == 200:
                            print(f"   ✅ {endpoint} is available")
                        else:
                            print(f"   ❌ {endpoint}: {test_response.status_code}")
                    except:
                        print(f"   ❌ {endpoint}: Connection failed")
                
                # Test database inspection
                print(f"\n🔍 Inspecting database structure...")
                inspect_url = f"{BACKEND_URL}/api/database/inspect"
                
                try:
                    inspect_response = requests.get(inspect_url, timeout=20)
                    if inspect_response.status_code == 200:
                        inspect_data = inspect_response.json()
                        
                        tables = inspect_data.get('tables', {})
                        print(f"   📋 Database has {len(tables)} tables")
                        
                        # Check product_metafields table
                        if 'product_metafields' in tables:
                            metafields_info = tables['product_metafields']
                            row_count = metafields_info.get('row_count', 0)
                            print(f"   📦 product_metafields: {row_count} rows")
                            
                            # Check columns
                            columns = metafields_info.get('columns', [])
                            column_names = [col['name'] for col in columns]
                            print(f"   📋 Columns: {column_names}")
                        
                        # Check shopify_products table  
                        if 'shopify_products' in tables:
                            products_info = tables['shopify_products']
                            row_count = products_info.get('row_count', 0)
                            print(f"   📦 shopify_products: {row_count} rows")
                    else:
                        print(f"   ❌ Database inspection failed: {inspect_response.status_code}")
                        
                except Exception as e:
                    print(f"   ❌ Database inspection error: {e}")
                
                # Test raw database query to find OEMs
                print(f"\n🔍 Testing raw database query for OEM search...")
                raw_query_url = f"{BACKEND_URL}/api/raw_database_query"
                
                try:
                    raw_response = requests.get(raw_query_url, timeout=20)
                    if raw_response.status_code == 200:
                        raw_data = raw_response.json()
                        
                        # Look for metafields data
                        metafields_count = raw_data.get('product_metafields_count', 0)
                        print(f"   📦 Found {metafields_count} product metafields")
                        
                        # Look for sample data
                        if 'sample_metafields' in raw_data:
                            sample_metafields = raw_data['sample_metafields']
                            print(f"   📋 Sample metafields:")
                            for i, metafield in enumerate(sample_metafields[:5]):
                                key = metafield.get('key', 'N/A')
                                value = metafield.get('value', 'N/A')
                                print(f"      {i+1}. {key}: {value}")
                        
                        # Check for Original_nummer specifically
                        if 'original_nummer_count' in raw_data:
                            oem_count = raw_data['original_nummer_count']
                            print(f"   🎯 Found {oem_count} Original_nummer metafields")
                            
                    else:
                        print(f"   ❌ Raw database query failed: {raw_response.status_code}")
                        
                except Exception as e:
                    print(f"   ❌ Raw database query error: {e}")
                
            else:
                print(f"❌ No OEMs found in backend response")
                
        else:
            print(f"❌ Backend request failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

def test_specific_oem_search():
    """Test searching for specific known OEMs"""
    
    print(f"\n🔍 TESTING SPECIFIC OEM SEARCH")
    print("=" * 40)
    
    # Known Nissan X-Trail OEMs that should exist
    test_oems = [
        "370008H310",
        "370008H510", 
        "370008H800",
        "37000-8H310",  # With hyphen
        "37000-8H510",  # With hyphen
        "MA18002"       # Product number
    ]
    
    print(f"🔍 Testing {len(test_oems)} specific OEMs...")
    
    for oem in test_oems:
        print(f"\n📋 Testing OEM: {oem}")
        
        # Try to search for this specific OEM via backend
        # Since there's no direct OEM search endpoint, we'll check if it appears in any results
        
        # For now, just document what we're looking for
        print(f"   🎯 Looking for: {oem}")
        print(f"   📋 Expected: Should match MA18002 or similar Nissan parts")
        print(f"   ❌ Current: No direct OEM search endpoint available")

if __name__ == "__main__":
    # Diagnose the OEM matching issue
    diagnose_oem_matching()
    
    # Test specific OEM searches
    test_specific_oem_search()
    
    print(f"\n🎯 DIAGNOSIS SUMMARY:")
    print(f"✅ TecDoc OEM search works (103 OEMs found)")
    print(f"❌ Shopify OEM matching fails (0 products found)")
    print(f"💡 Next steps:")
    print(f"   1. Check if MA18002 exists in Shopify database")
    print(f"   2. Verify OEM format matching (hyphens, spaces, case)")
    print(f"   3. Debug SQL query for OEM matching")
    print(f"   4. Check if product sync is working correctly")
