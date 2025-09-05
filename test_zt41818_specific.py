#!/usr/bin/env python3
"""
Test ZT41818 specifically with longer timeout to debug the issue
"""

import requests
import json
import time

BACKEND_URL = "https://web-production-0809b.up.railway.app"

def test_zt41818_with_patience():
    """Test ZT41818 with longer timeout and detailed monitoring"""
    
    print("🔍 TESTING ZT41818 WITH EXTENDED TIMEOUT")
    print("=" * 45)
    
    license_plate = "ZT41818"
    search_url = f"{BACKEND_URL}/api/car_parts_search"
    payload = {"license_plate": license_plate}
    
    print(f"📡 Testing: {license_plate} (Nissan X-Trail 2006)")
    print(f"🕐 Using 60-second timeout...")
    
    try:
        start_time = time.time()
        response = requests.post(search_url, json=payload, timeout=60)
        duration = time.time() - start_time
        
        print(f"⏱️  Response time: {duration:.2f}s")
        print(f"📊 Status code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            available_oems = data.get('available_oems', 'unknown')
            compatible_oems = data.get('compatible_oems', 'unknown')
            shopify_parts = data.get('shopify_parts', [])
            message = data.get('message', 'No message')
            
            print(f"✅ Available OEMs: {available_oems}")
            print(f"✅ Compatible OEMs: {compatible_oems}")
            print(f"✅ Shopify parts: {len(shopify_parts)}")
            print(f"✅ Message: {message}")
            
            # Check performance breakdown
            performance = data.get('performance', {})
            if performance:
                print(f"\n📊 Performance breakdown:")
                for key, value in performance.items():
                    print(f"   {key}: {value}")
            
            # If we got OEMs but no products, that's the matching issue
            if available_oems > 0 and len(shopify_parts) == 0:
                print(f"\n🎯 DIAGNOSIS: TecDoc works ({available_oems} OEMs), but OEM-to-Shopify matching fails")
                print(f"   This confirms the issue is in search_products_by_oem_optimized()")
                return "oem_matching_issue"
            
            # If we got both OEMs and products, it's working
            elif available_oems > 0 and len(shopify_parts) > 0:
                print(f"\n✅ SUCCESS: Both TecDoc and OEM matching work!")
                return "success"
            
            # If no OEMs, it's a TecDoc issue
            elif available_oems == 0:
                print(f"\n❌ DIAGNOSIS: TecDoc returns no OEMs for ZT41818")
                print(f"   This suggests the new live TecDoc integration has an issue")
                return "tecdoc_issue"
                
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return "http_error"
            
    except requests.exceptions.Timeout:
        print(f"⏰ TIMEOUT after 60 seconds")
        print(f"   This suggests the new TecDoc integration is hanging/looping")
        return "timeout"
        
    except Exception as e:
        print(f"❌ Exception: {e}")
        return "exception"

def compare_working_vs_broken():
    """Compare YZ99554 (working) vs ZT41818 (broken) to identify differences"""
    
    print(f"\n🔍 COMPARING WORKING VS BROKEN LICENSE PLATES")
    print("=" * 50)
    
    plates = [
        ("YZ99554", "Mercedes GLK (working)"),
        ("ZT41818", "Nissan X-Trail (broken)")
    ]
    
    for plate, description in plates:
        print(f"\n📡 Testing: {plate} ({description})")
        
        try:
            start_time = time.time()
            response = requests.post(
                f"{BACKEND_URL}/api/car_parts_search", 
                json={"license_plate": plate}, 
                timeout=15
            )
            duration = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                available_oems = data.get('available_oems', 0)
                compatible_oems = data.get('compatible_oems', 0)
                
                print(f"   ✅ Time: {duration:.2f}s")
                print(f"   ✅ Available OEMs: {available_oems}")
                print(f"   ✅ Compatible OEMs: {compatible_oems}")
                
                # Check vehicle info
                vehicle_info = data.get('vehicle_info', {})
                make = vehicle_info.get('make', 'Unknown')
                model = vehicle_info.get('model', 'Unknown')
                year = vehicle_info.get('year', 'Unknown')
                print(f"   ✅ Vehicle: {make} {model} {year}")
                
            else:
                print(f"   ❌ Error: {response.status_code}")
                
        except requests.exceptions.Timeout:
            print(f"   ⏰ TIMEOUT")
        except Exception as e:
            print(f"   ❌ Exception: {e}")

if __name__ == "__main__":
    # Test ZT41818 with patience
    result = test_zt41818_with_patience()
    
    # Compare working vs broken
    compare_working_vs_broken()
    
    print(f"\n🎯 DIAGNOSIS RESULT: {result}")
    
    if result == "oem_matching_issue":
        print(f"✅ TecDoc works, but OEM-to-Shopify matching fails")
        print(f"🔧 Need to debug search_products_by_oem_optimized() function")
    elif result == "tecdoc_issue":
        print(f"❌ TecDoc integration issue for Nissan X-Trail")
        print(f"🔧 Need to debug get_oem_numbers_from_rapidapi_tecdoc() for this vehicle")
    elif result == "timeout":
        print(f"⏰ TecDoc integration is hanging/looping")
        print(f"🔧 Need to check for infinite loops in new live TecDoc code")
