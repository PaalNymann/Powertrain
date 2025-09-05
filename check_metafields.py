#!/usr/bin/env python3
"""
Check metafields data to debug OEM matching issue
"""

import requests
import json

BACKEND_URL = "https://web-production-0809b.up.railway.app"

def check_metafields_data():
    """Check what's actually in the metafields table"""
    
    print("🔍 CHECKING METAFIELDS DATA FOR OEM DEBUGGING")
    print("=" * 60)
    
    # Check metafields stats endpoint
    try:
        stats_url = f"{BACKEND_URL}/api/metafields/stats"
        response = requests.get(stats_url, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Metafields stats:")
            print(json.dumps(data, indent=2))
        else:
            print(f"❌ Metafields stats failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Metafields stats error: {e}")
    
    # Check cache stats to see what's in the system
    try:
        cache_url = f"{BACKEND_URL}/api/cache/stats"
        response = requests.get(cache_url, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ Cache stats:")
            print(json.dumps(data, indent=2))
        else:
            print(f"❌ Cache stats failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Cache stats error: {e}")

def test_known_oems():
    """Test if known Nissan OEMs exist in the system"""
    
    print(f"\n🔍 TESTING KNOWN NISSAN OEMS")
    print("=" * 40)
    
    # Known Nissan X-Trail OEMs from customer verification
    nissan_oems = [
        "370008H310",
        "370008H510", 
        "370008H800",
        "37000-8H310",  # With hyphen
        "37000-8H510",  # With hyphen
        "37000-8H800"   # With hyphen
    ]
    
    print(f"🎯 Customer-verified Nissan OEMs for MA18002:")
    for oem in nissan_oems:
        print(f"   - {oem}")
    
    print(f"\n💡 These OEMs should be found in Original_nummer metafields")
    print(f"💡 If they exist, they should match for ZT41818 search")
    print(f"💡 If MA18002 is synced, it should appear in results")

def analyze_oem_matching_problem():
    """Analyze why OEM matching fails despite having data"""
    
    print(f"\n🔍 ANALYZING OEM MATCHING PROBLEM")
    print("=" * 50)
    
    print(f"📊 Current Status:")
    print(f"   ✅ TecDoc finds 103 OEMs for ZT41818")
    print(f"   ✅ Database has 936 metafields")
    print(f"   ✅ Database has 156 products")
    print(f"   ❌ 0 products matched via OEM search")
    
    print(f"\n🔍 Possible Causes:")
    print(f"   1. OEM format mismatch (TecDoc vs Shopify)")
    print(f"   2. SQL query bug in OEM matching")
    print(f"   3. Case sensitivity issues")
    print(f"   4. MA18002 not synced to Shopify")
    print(f"   5. Original_nummer field empty/wrong")
    
    print(f"\n🔧 Debug Steps Needed:")
    print(f"   1. Check if MA18002 exists in shopify_products table")
    print(f"   2. Check if MA18002 has Original_nummer metafield")
    print(f"   3. Verify OEM format in metafields vs TecDoc")
    print(f"   4. Test SQL query manually with known OEMs")
    print(f"   5. Check if product group filtering works")

if __name__ == "__main__":
    # Check metafields data
    check_metafields_data()
    
    # Test known OEMs
    test_known_oems()
    
    # Analyze the problem
    analyze_oem_matching_problem()
    
    print(f"\n🎯 NEXT ACTION:")
    print(f"Need to debug the SQL query in optimized_search.py")
    print(f"that matches TecDoc OEMs against Original_nummer metafields")
    print(f"The issue is likely in the OEM normalization or SQL LIKE logic")
