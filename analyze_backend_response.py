#!/usr/bin/env python3
"""
Analyze detailed backend response for ZT41818 to understand OEM matching status
"""

import requests
import json

BACKEND_URL = "https://web-production-0809b.up.railway.app"

def analyze_zt41818_response():
    """Analyze the detailed backend response for ZT41818"""
    
    print("🔍 ANALYZING DETAILED BACKEND RESPONSE FOR ZT41818")
    print("=" * 60)
    
    license_plate = "ZT41818"
    search_url = f"{BACKEND_URL}/api/car_parts_search"
    payload = {"license_plate": license_plate}
    
    try:
        response = requests.post(search_url, json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            print("📊 COMPLETE BACKEND RESPONSE ANALYSIS:")
            print("=" * 50)
            
            # Analyze each key in detail
            for key, value in data.items():
                print(f"\n🔍 {key.upper()}:")
                
                if key == 'vehicle_info':
                    if isinstance(value, dict):
                        for sub_key, sub_value in value.items():
                            print(f"   {sub_key}: {sub_value}")
                    else:
                        print(f"   {value}")
                        
                elif key == 'available_oems':
                    if isinstance(value, list):
                        print(f"   Count: {len(value)}")
                        if value:
                            print(f"   Sample OEMs: {', '.join(value[:10])}")
                            if len(value) > 10:
                                print(f"   ... and {len(value) - 10} more")
                        else:
                            print(f"   ❌ No available OEMs found")
                    else:
                        print(f"   {value}")
                        
                elif key == 'compatible_oems':
                    if isinstance(value, list):
                        print(f"   Count: {len(value)}")
                        if value:
                            print(f"   Sample OEMs: {', '.join(value[:10])}")
                            if len(value) > 10:
                                print(f"   ... and {len(value) - 10} more")
                        else:
                            print(f"   ❌ No compatible OEMs found")
                    else:
                        print(f"   {value}")
                        
                elif key == 'matching_products':
                    if isinstance(value, list):
                        print(f"   Count: {len(value)}")
                        if value:
                            for i, product in enumerate(value[:3]):
                                title = product.get('title', 'N/A')
                                handle = product.get('handle', 'N/A')
                                print(f"   {i+1}. {title} (Handle: {handle})")
                        else:
                            print(f"   ❌ No matching products found")
                    else:
                        print(f"   {value}")
                        
                elif key == 'message':
                    print(f"   {value}")
                    
                else:
                    print(f"   {value}")
            
            # Key analysis
            print(f"\n🎯 KEY ANALYSIS:")
            
            available_oems = data.get('available_oems', [])
            compatible_oems = data.get('compatible_oems', [])
            matching_products = data.get('matching_products', [])
            
            if not available_oems:
                print(f"❌ ISSUE: No available OEMs found - TecDoc lookup may have failed")
            elif not compatible_oems:
                print(f"❌ ISSUE: No compatible OEMs found - TecDoc compatibility check failed")
            elif not matching_products:
                print(f"❌ ISSUE: No matching products found - Shopify OEM matching failed")
                print(f"💡 This means TecDoc found OEMs but no Shopify products match them")
            else:
                print(f"✅ SUCCESS: Full pipeline working")
            
            # Check if our target Nissan OEMs are present
            target_oems = ["370008H310", "370008H510", "370008H800"]
            found_target_oems = []
            
            all_oems = available_oems + compatible_oems
            for target_oem in target_oems:
                if any(target_oem in oem for oem in all_oems):
                    found_target_oems.append(target_oem)
            
            if found_target_oems:
                print(f"✅ Found target Nissan OEMs: {', '.join(found_target_oems)}")
            else:
                print(f"❌ Target Nissan OEMs not found in backend response")
                print(f"💡 Expected: {', '.join(target_oems)}")
            
            return data
            
        else:
            print(f"❌ Backend request failed: {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        return None

def test_direct_oem_search():
    """Test if we can search for products by specific OEM numbers"""
    
    print(f"\n🔍 TESTING DIRECT OEM SEARCH IN SHOPIFY DATABASE")
    print("=" * 50)
    
    # Test if there's a direct OEM search endpoint
    target_oems = ["370008H310", "37000-8H310", "MA18002"]
    
    for oem in target_oems:
        print(f"\n🔍 Testing OEM search for: {oem}")
        
        # Try different possible endpoints
        possible_endpoints = [
            f"/api/search_oem/{oem}",
            f"/api/products/oem/{oem}",
            f"/test/oem/{oem}",
            f"/debug/oem/{oem}"
        ]
        
        for endpoint in possible_endpoints:
            url = f"{BACKEND_URL}{endpoint}"
            
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    print(f"   ✅ Found endpoint: {endpoint}")
                    data = response.json()
                    print(f"   Response: {data}")
                    break
                elif response.status_code != 404:
                    print(f"   Status {response.status_code}: {endpoint}")
            except:
                pass
        else:
            print(f"   ❌ No working OEM search endpoint found for {oem}")

if __name__ == "__main__":
    # Analyze the detailed backend response
    response_data = analyze_zt41818_response()
    
    # Test direct OEM search capabilities
    test_direct_oem_search()
    
    print(f"\n🎯 NEXT STEPS:")
    if response_data:
        available_oems = response_data.get('available_oems', [])
        compatible_oems = response_data.get('compatible_oems', [])
        matching_products = response_data.get('matching_products', [])
        
        if not available_oems:
            print(f"1. Debug TecDoc OEM extraction for ZT41818")
            print(f"2. Ensure VIN/chassis number is correctly extracted from SVV")
            print(f"3. Verify TecDoc API calls are working")
        elif not compatible_oems:
            print(f"1. Debug TecDoc compatibility filtering")
            print(f"2. Check if compatibility logic is too restrictive")
        elif not matching_products:
            print(f"1. Debug Shopify OEM matching logic")
            print(f"2. Verify MA18002 and similar products are synced with correct OEMs")
            print(f"3. Check OEM normalization (spaces, hyphens, case sensitivity)")
        else:
            print(f"✅ System is working - investigate why MA18002 specifically is missing")
    else:
        print(f"1. Fix backend connectivity issues")
        print(f"2. Check backend logs for errors")
