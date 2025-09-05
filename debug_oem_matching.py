#!/usr/bin/env python3
"""
Debug OEM matching between TecDoc and Shopify database
"""

import requests
import json

BACKEND_URL = "https://web-production-0809b.up.railway.app"

def test_oem_matching_directly():
    """Test OEM matching directly using backend debug endpoints"""
    
    print("🔍 DEBUGGING OEM MATCHING BETWEEN TECDOC AND SHOPIFY")
    print("=" * 60)
    
    # First, get the OEMs that TecDoc returns for ZT41818
    print("📡 Step 1: Get TecDoc OEMs for ZT41818...")
    search_url = f"{BACKEND_URL}/api/car_parts_search"
    payload = {"license_plate": "ZT41818"}
    
    try:
        response = requests.post(search_url, json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            available_oems = data.get('available_oems', 0)
            print(f"✅ TecDoc returned {available_oems} OEMs")
            
            # Get performance details
            performance = data.get('performance', {})
            step2_time = performance.get('step2_time', 0)
            step3_time = performance.get('step3_time', 0)
            
            print(f"⏱️  Step 2 (TecDoc): {step2_time:.2f}s")
            print(f"⏱️  Step 3 (OEM matching): {step3_time:.2f}s")
            
            if step3_time < 0.5:
                print("⚠️  Step 3 is suspiciously fast - OEM matching may not be working")
            
        else:
            print(f"❌ Search failed: {response.status_code}")
            return
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return
    
    # Check metafields directly
    print(f"\n🔍 Step 2: Check metafields in database...")
    try:
        metafields_url = f"{BACKEND_URL}/api/metafields/stats"
        response = requests.get(metafields_url, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Metafields stats:")
            print(json.dumps(data, indent=2))
        else:
            print(f"❌ Metafields stats failed: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Metafields check error: {e}")
    
    # Test known Nissan OEMs directly
    print(f"\n🔍 Step 3: Test known Nissan OEMs...")
    
    # Customer-verified Nissan OEMs for MA18002
    test_oems = [
        "370008H310",
        "370008H510", 
        "370008H800",
        "37000-8H310",
        "37000-8H510",
        "37000-8H800"
    ]
    
    print(f"🎯 Testing customer-verified Nissan OEMs:")
    for oem in test_oems:
        print(f"   - {oem}")
    
    print(f"\n💡 If these OEMs exist in Original_nummer metafields,")
    print(f"💡 and MA18002 is synced to Shopify, it should appear in results")
    
    # Check if we can query the database directly for these OEMs
    print(f"\n🔍 Step 4: Direct database OEM check needed...")
    print(f"Need to check if any of these OEMs exist in product_metafields table")
    print(f"with key='Original_nummer' and if MA18002 product exists")

def analyze_oem_format_mismatch():
    """Analyze potential OEM format differences between TecDoc and Shopify"""
    
    print(f"\n🔍 ANALYZING POTENTIAL OEM FORMAT MISMATCH")
    print("=" * 50)
    
    print(f"📊 Known Issues:")
    print(f"   1. TecDoc may return OEMs in different format than Shopify")
    print(f"   2. Case sensitivity (uppercase vs lowercase)")
    print(f"   3. Hyphen/space differences (37000-8H310 vs 370008H310)")
    print(f"   4. Leading/trailing whitespace")
    print(f"   5. Prefix/suffix variations (A prefix, etc.)")
    
    print(f"\n🔧 Debug Steps Needed:")
    print(f"   1. Check what OEMs TecDoc actually returns for ZT41818")
    print(f"   2. Check what OEMs exist in Original_nummer metafields")
    print(f"   3. Compare formats and identify normalization needed")
    print(f"   4. Test SQL LIKE patterns in search_products_by_oem_optimized()")
    
    print(f"\n💡 The search_products_by_oem_optimized() function has extensive")
    print(f"💡 OEM variation logic - but it may not be called or working correctly")

if __name__ == "__main__":
    # Test OEM matching
    test_oem_matching_directly()
    
    # Analyze format issues
    analyze_oem_format_mismatch()
    
    print(f"\n🎯 NEXT ACTION:")
    print(f"Need to debug why search_products_by_oem_optimized() returns no products")
    print(f"despite having 936 metafields and comprehensive OEM variation logic")
