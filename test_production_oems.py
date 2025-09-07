#!/usr/bin/env python3
"""
Test production database OEM matching via API calls
"""

import requests
import json

def test_production_oems():
    """Test production database OEM matching for MA18002 and Nissan OEMs"""
    
    base_url = "https://web-production-0809b.up.railway.app"
    
    print("🔍 TESTING PRODUCTION DATABASE OEM MATCHING")
    print("=" * 60)
    
    # Test 1: Check if ZT41818 search finds any OEMs and products
    print("\n📊 Test 1: ZT41818 search results...")
    try:
        response = requests.post(
            f"{base_url}/api/car_parts_search",
            json={"license_plate": "ZT41818"},
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"   Status: {response.status_code}")
            print(f"   Available OEMs: {data.get('available_oems', 0)}")
            print(f"   Compatible OEMs: {data.get('compatible_oems', 0)}")
            print(f"   Shopify parts: {len(data.get('shopify_parts', []))}")
            print(f"   MA18002 found: {data.get('performance', {}).get('ma18002_found', False)}")
            print(f"   Total time: {data.get('performance', {}).get('total_time', 0)}s")
            
            # Show first few parts if any
            parts = data.get('shopify_parts', [])
            if parts:
                print(f"   First few parts:")
                for i, part in enumerate(parts[:3]):
                    print(f"      {i+1}. {part.get('title', 'Unknown')} ({part.get('sku', 'No SKU')})")
            else:
                print("   ❌ No parts found despite OEMs being available")
        else:
            print(f"   ❌ API Error: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"   ❌ Request failed: {e}")
    
    # Test 2: Try a known working vehicle (if any)
    print("\n🔍 Test 2: Testing known working vehicle YZ99554...")
    try:
        response = requests.post(
            f"{base_url}/api/car_parts_search",
            json={"license_plate": "YZ99554"},
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"   Status: {response.status_code}")
            print(f"   Available OEMs: {data.get('available_oems', 0)}")
            print(f"   Compatible OEMs: {data.get('compatible_oems', 0)}")
            print(f"   Shopify parts: {len(data.get('shopify_parts', []))}")
            print(f"   Total time: {data.get('performance', {}).get('total_time', 0)}s")
            
            if data.get('shopify_parts'):
                print("   ✅ YZ99554 returns parts - database matching works for some vehicles")
            else:
                print("   ❌ YZ99554 also returns no parts - database matching broken")
        else:
            print(f"   ❌ API Error: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Request failed: {e}")
    
    # Test 3: Try another test vehicle
    print("\n🔍 Test 3: Testing KH66644 (Volkswagen Tiguan)...")
    try:
        response = requests.post(
            f"{base_url}/api/car_parts_search",
            json={"license_plate": "KH66644"},
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"   Status: {response.status_code}")
            print(f"   Available OEMs: {data.get('available_oems', 0)}")
            print(f"   Compatible OEMs: {data.get('compatible_oems', 0)}")
            print(f"   Shopify parts: {len(data.get('shopify_parts', []))}")
            print(f"   Total time: {data.get('performance', {}).get('total_time', 0)}s")
            
            if data.get('shopify_parts'):
                print("   ✅ KH66644 returns parts - database matching works for VW")
            else:
                print("   ❌ KH66644 also returns no parts")
        else:
            print(f"   ❌ API Error: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Request failed: {e}")
    
    print("\n" + "=" * 60)
    print("🎯 PRODUCTION OEM TEST COMPLETE")
    print("\n📋 ANALYSIS:")
    print("   If all vehicles return 0 parts despite finding OEMs:")
    print("   → Database OEM matching is broken (normalization/query issue)")
    print("   If some vehicles work but ZT41818 doesn't:")
    print("   → TecDoc OEMs for Nissan don't match database format")
    print("   If no vehicles work:")
    print("   → Database metafields missing or search function broken")

if __name__ == "__main__":
    test_production_oems()
