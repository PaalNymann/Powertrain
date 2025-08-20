#!/usr/bin/env python3
"""
Test the API directly to see what's happening
"""

import requests
import json

def test_api_direct():
    """Test the API directly for all three license plates"""
    
    print("🧪 TESTING API DIRECTLY")
    print("=" * 50)
    
    base_url = "https://web-production-0809b.up.railway.app/api/car_parts_search"
    
    test_plates = ["YZ99554", "KH66644", "RJ62438"]
    
    for plate in test_plates:
        print(f"\n🚗 Testing {plate}:")
        print("-" * 30)
        
        try:
            url = f"{base_url}?regnr={plate}"
            print(f"🌐 Calling: {url}")
            
            response = requests.get(url, timeout=30)
            
            print(f"📊 Status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    
                    # Check key fields
                    vehicle_info = data.get('vehicle_info', {})
                    parts = data.get('shopify_parts', [])
                    message = data.get('message', '')
                    
                    print(f"🚗 Vehicle: {vehicle_info.get('make', 'Unknown')} {vehicle_info.get('model', 'Unknown')} {vehicle_info.get('year', 'Unknown')}")
                    print(f"🔍 Parts found: {len(parts)}")
                    print(f"💬 Message: {message}")
                    
                    if len(parts) == 0:
                        print(f"❌ NO PARTS FOUND - This is the problem!")
                    else:
                        print(f"✅ Found {len(parts)} parts")
                        # Show first part
                        if parts:
                            first_part = parts[0]
                            print(f"   First part: {first_part.get('title', 'Unknown')}")
                    
                except json.JSONDecodeError as e:
                    print(f"❌ JSON decode error: {e}")
                    print(f"📄 Raw response: {response.text[:200]}...")
            else:
                print(f"❌ HTTP Error: {response.status_code}")
                print(f"📄 Response: {response.text[:200]}...")
                
        except requests.exceptions.Timeout:
            print(f"⏰ TIMEOUT - API took too long to respond")
        except requests.exceptions.RequestException as e:
            print(f"❌ Request error: {e}")
    
    print(f"\n🎯 SUMMARY:")
    print("If all three return 0 parts, the problem is in:")
    print("1. Cache lookup failing")
    print("2. TecDoc fallback failing") 
    print("3. OEM matching logic failing")
    print("4. Database connection issues")

if __name__ == "__main__":
    test_api_direct()
