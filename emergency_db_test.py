#!/usr/bin/env python3
"""
Emergency database connectivity and metafields test
"""

import requests
import json

def emergency_database_test():
    """Test if database has any products and metafields at all"""
    
    print("🚨 EMERGENCY DATABASE CONNECTIVITY TEST")
    print("=" * 50)
    
    # Test basic API connectivity
    try:
        response = requests.get("https://web-production-0809b.up.railway.app/", timeout=10)
        print(f"✅ API connectivity: {response.status_code}")
    except Exception as e:
        print(f"❌ API connectivity failed: {e}")
        return
    
    # Test a simple search that should work
    print("\n🔍 Testing simple search functionality...")
    
    # Try the old working approach - check if any endpoint works
    test_vehicles = ["YZ99554", "KH66644", "RJ62438"]
    
    for vehicle in test_vehicles:
        print(f"\n📋 Testing {vehicle}...")
        try:
            response = requests.post(
                "https://web-production-0809b.up.railway.app/api/car_parts_search",
                json={"license_plate": vehicle},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                oems = data.get('available_oems', 0)
                parts = len(data.get('shopify_parts', []))
                time_taken = data.get('performance', {}).get('total_time', 0)
                
                print(f"   Status: ✅ {response.status_code}")
                print(f"   OEMs found: {oems}")
                print(f"   Parts found: {parts}")
                print(f"   Time: {time_taken}s")
                
                if parts > 0:
                    print(f"   🎉 {vehicle} WORKS! Database matching is functional")
                    return True
                else:
                    print(f"   ❌ {vehicle} finds OEMs but no parts")
            else:
                print(f"   ❌ API Error: {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                
        except Exception as e:
            print(f"   ❌ Request failed: {e}")
    
    print("\n🚨 CRITICAL: ALL VEHICLES RETURN 0 PARTS")
    print("   This indicates database metafields are missing or broken")
    print("   Need immediate restoration of working database search")
    
    return False

if __name__ == "__main__":
    emergency_database_test()
