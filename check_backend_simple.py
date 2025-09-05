#!/usr/bin/env python3
"""
Simple backend response checker to see exact response format
"""

import requests
import json

BACKEND_URL = "https://web-production-0809b.up.railway.app"

def check_backend_response():
    """Check the exact backend response format"""
    
    print("🔍 CHECKING BACKEND RESPONSE FORMAT")
    print("=" * 50)
    
    license_plate = "ZT41818"
    search_url = f"{BACKEND_URL}/api/car_parts_search"
    payload = {"license_plate": license_plate}
    
    try:
        response = requests.post(search_url, json=payload, timeout=30)
        
        print(f"📊 Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"📋 Response keys: {list(data.keys())}")
            
            # Check each key and its type
            for key, value in data.items():
                print(f"\n🔍 {key}:")
                print(f"   Type: {type(value)}")
                
                if isinstance(value, (list, dict)):
                    if isinstance(value, list):
                        print(f"   Length: {len(value)}")
                        if value and len(value) <= 5:
                            print(f"   Content: {value}")
                        elif value:
                            print(f"   First 3 items: {value[:3]}")
                    else:
                        print(f"   Keys: {list(value.keys()) if value else 'Empty dict'}")
                else:
                    print(f"   Value: {value}")
            
            print(f"\n📋 FULL RESPONSE:")
            print(json.dumps(data, indent=2))
            
        else:
            print(f"❌ Request failed: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_backend_response()
