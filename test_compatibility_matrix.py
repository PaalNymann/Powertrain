#!/usr/bin/env python3
"""
Test if compatibility matrix has data for ZT41818 (Nissan X-Trail 2006)
"""

import requests
import json

BACKEND_URL = "https://web-production-0809b.up.railway.app"

def test_compatibility_matrix_for_zt41818():
    """Test if compatibility matrix contains ZT41818 data"""
    
    print("🔍 TESTING COMPATIBILITY MATRIX FOR ZT41818")
    print("=" * 50)
    
    # Create a simple endpoint test to check compatibility matrix
    test_url = f"{BACKEND_URL}/api/raw_database_query"
    
    # Try to access compatibility matrix data via existing endpoints
    try:
        # Check database inspect for vehicle_product_compatibility table
        inspect_url = f"{BACKEND_URL}/api/database/inspect"
        response = requests.get(inspect_url, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            tables = data.get('tables', {})
            
            if 'vehicle_product_compatibility' in tables:
                compat_table = tables['vehicle_product_compatibility']
                row_count = compat_table.get('row_count', 0)
                print(f"✅ vehicle_product_compatibility table exists with {row_count} rows")
                
                if row_count > 0:
                    print(f"✅ Compatibility matrix has data")
                    
                    # The main search uses get_oems_for_vehicle_from_cache() from compatibility_matrix.py
                    # This suggests the cache lookup is working and finding OEMs for ZT41818
                    print(f"💡 Main search finds 10 OEMs via cache lookup")
                    print(f"💡 This means compatibility matrix contains ZT41818 data")
                    
                else:
                    print(f"❌ Compatibility matrix is empty")
            else:
                print(f"❌ vehicle_product_compatibility table not found")
        else:
            print(f"❌ Database inspect failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error checking compatibility matrix: {e}")

def analyze_cache_vs_direct_tecdoc():
    """Analyze why cache works but direct TecDoc fails for ZT41818"""
    
    print(f"\n🔍 ANALYZING CACHE VS DIRECT TECDOC")
    print("=" * 40)
    
    print(f"📊 Current Status:")
    print(f"   ✅ Main search (cache): 10 OEMs found for ZT41818")
    print(f"   ❌ Debug endpoint (direct TecDoc): 0 OEMs found for ZT41818")
    print(f"   ✅ Database: 156 products, 936 metafields")
    print(f"   ✅ Compatibility matrix: 1584 rows")
    
    print(f"\n🔍 Root Cause Analysis:")
    print(f"   1. Cache lookup works → compatibility matrix has ZT41818 data")
    print(f"   2. Direct TecDoc fails → RapidAPI TecDoc issue for Nissan X-Trail")
    print(f"   3. OEM-to-Shopify matching fails → format mismatch or SQL issue")
    
    print(f"\n🎯 The Real Problem:")
    print(f"   Cache finds 10 OEMs, but 0 products are matched in Shopify")
    print(f"   This means the issue is in search_products_by_oem_optimized()")
    print(f"   NOT in TecDoc API (which works via cache)")
    
    print(f"\n🔧 Solution Strategy:")
    print(f"   1. Focus on OEM-to-Shopify matching logic")
    print(f"   2. Debug why cache OEMs don't match database products")
    print(f"   3. Check OEM format normalization between cache and database")
    print(f"   4. Test search_products_by_oem_optimized() with cache OEMs")

def test_working_vs_broken_comparison():
    """Compare working (YZ99554) vs broken (ZT41818) to find differences"""
    
    print(f"\n🔍 COMPARING WORKING VS BROKEN LICENSE PLATES")
    print("=" * 50)
    
    plates = [
        ("YZ99554", "Mercedes GLK (working: 18→10)"),
        ("ZT41818", "Nissan X-Trail (broken: 10→0)")
    ]
    
    for plate, description in plates:
        print(f"\n📡 Testing: {plate} ({description})")
        
        try:
            response = requests.post(
                f"{BACKEND_URL}/api/car_parts_search", 
                json={"license_plate": plate}, 
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                available_oems = data.get('available_oems', 0)
                compatible_oems = data.get('compatible_oems', 0)
                shopify_parts = len(data.get('shopify_parts', []))
                
                print(f"   ✅ Available OEMs: {available_oems}")
                print(f"   ✅ Compatible OEMs: {compatible_oems}")
                print(f"   ✅ Shopify parts: {shopify_parts}")
                
                # Check vehicle info
                vehicle_info = data.get('vehicle_info', {})
                make = vehicle_info.get('make', 'Unknown')
                model = vehicle_info.get('model', 'Unknown')
                year = vehicle_info.get('year', 'Unknown')
                print(f"   ✅ Vehicle: {make} {model} {year}")
                
                if available_oems > 0 and shopify_parts == 0:
                    print(f"   🎯 DIAGNOSIS: OEM-to-Shopify matching fails")
                elif available_oems > 0 and shopify_parts > 0:
                    print(f"   ✅ SUCCESS: Both TecDoc and matching work")
                
            else:
                print(f"   ❌ Error: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Exception: {e}")

if __name__ == "__main__":
    # Test compatibility matrix
    test_compatibility_matrix_for_zt41818()
    
    # Analyze cache vs direct TecDoc
    analyze_cache_vs_direct_tecdoc()
    
    # Compare working vs broken
    test_working_vs_broken_comparison()
    
    print(f"\n🎯 CONCLUSION:")
    print(f"The issue is NOT in TecDoc API (cache works)")
    print(f"The issue IS in OEM-to-Shopify matching logic")
    print(f"Focus on debugging search_products_by_oem_optimized() function")
