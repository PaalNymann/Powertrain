#!/usr/bin/env python3
"""
Test different TecDoc endpoints to find vehicle compatibility data
"""

import requests
import json

# RapidAPI TecDoc Configuration
RAPIDAPI_KEY = "48a6ede874mshe38f052cb6a6109p12916fjsn0d0c0912c5ed"
BASE_URL = "https://tecdoc-catalog.p.rapidapi.com"
HEADERS = {
    'x-rapidapi-host': 'tecdoc-catalog.p.rapidapi.com',
    'x-rapidapi-key': RAPIDAPI_KEY
}

LANG_ID = 4  # English
COUNTRY_ID = 62  # Germany
TYPE_ID = 1  # Passenger cars

def test_vehicle_compatibility_endpoints():
    """Test different endpoints to find vehicle compatibility data"""
    
    print("🔍 TESTING VEHICLE COMPATIBILITY ENDPOINTS")
    print("=" * 50)
    
    article_id = "261965"  # Known Nissan article ID
    
    # Test different endpoint patterns for vehicle compatibility
    test_endpoints = [
        # Pattern 1: Article vehicles
        f"/articles/{article_id}/vehicles/lang-id/{LANG_ID}/country-filter-id/{COUNTRY_ID}/type-id/{TYPE_ID}",
        
        # Pattern 2: Article compatibility
        f"/articles/{article_id}/compatibility/lang-id/{LANG_ID}/country-filter-id/{COUNTRY_ID}/type-id/{TYPE_ID}",
        
        # Pattern 3: Article applications
        f"/articles/{article_id}/applications/lang-id/{LANG_ID}/country-filter-id/{COUNTRY_ID}/type-id/{TYPE_ID}",
        
        # Pattern 4: Vehicle applications
        f"/vehicles/applications/article-id/{article_id}/lang-id/{LANG_ID}/country-filter-id/{COUNTRY_ID}/type-id/{TYPE_ID}",
        
        # Pattern 5: Article vehicle list
        f"/articles/vehicle-list/article-id/{article_id}/lang-id/{LANG_ID}/country-filter-id/{COUNTRY_ID}/type-id/{TYPE_ID}",
        
        # Pattern 6: Compatibility check
        f"/compatibility/article-id/{article_id}/lang-id/{LANG_ID}/country-filter-id/{COUNTRY_ID}/type-id/{TYPE_ID}",
        
        # Pattern 7: Article cars
        f"/articles/{article_id}/cars/lang-id/{LANG_ID}/country-filter-id/{COUNTRY_ID}/type-id/{TYPE_ID}",
        
        # Pattern 8: Vehicle compatibility
        f"/vehicle-compatibility/article-id/{article_id}/lang-id/{LANG_ID}/country-filter-id/{COUNTRY_ID}/type-id/{TYPE_ID}",
        
        # Pattern 9: Applications list
        f"/applications/list/article-id/{article_id}/lang-id/{LANG_ID}/country-filter-id/{COUNTRY_ID}/type-id/{TYPE_ID}",
        
        # Pattern 10: Article models
        f"/articles/{article_id}/models/lang-id/{LANG_ID}/country-filter-id/{COUNTRY_ID}/type-id/{TYPE_ID}",
    ]
    
    for i, endpoint in enumerate(test_endpoints, 1):
        print(f"\n🔍 Test {i}: {endpoint}")
        url = BASE_URL + endpoint
        
        try:
            response = requests.get(url, headers=HEADERS, timeout=10)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if isinstance(data, dict):
                        print(f"   ✅ SUCCESS! Response type: dict")
                        print(f"   Keys: {list(data.keys())}")
                        
                        # Look for vehicle data
                        vehicle_count = 0
                        for key, value in data.items():
                            if isinstance(value, list):
                                vehicle_count += len(value)
                                print(f"   {key}: {len(value)} items")
                                if value and len(value) > 0:
                                    print(f"   First item: {value[0]}")
                            else:
                                print(f"   {key}: {value}")
                        
                        if vehicle_count > 0:
                            print(f"   🎯 FOUND VEHICLE DATA! Total items: {vehicle_count}")
                            return endpoint, data
                            
                    elif isinstance(data, list):
                        print(f"   ✅ SUCCESS! Response type: list with {len(data)} items")
                        if data:
                            print(f"   First item: {data[0]}")
                            print(f"   🎯 FOUND VEHICLE DATA! List with {len(data)} items")
                            return endpoint, data
                    else:
                        print(f"   Data: {data}")
                        
                except Exception as e:
                    print(f"   Raw response: {response.text[:200]}")
                    
            elif response.status_code == 404:
                print(f"   ❌ Endpoint not found")
            elif response.status_code == 400:
                print(f"   ⚠️ Bad request")
                print(f"   Error: {response.text[:100]}")
            else:
                print(f"   Status {response.status_code}: {response.text[:100]}")
                
        except Exception as e:
            print(f"   Exception: {e}")
    
    print(f"\n❌ No vehicle compatibility endpoint found")
    return None, None

if __name__ == "__main__":
    endpoint, data = test_vehicle_compatibility_endpoints()
    
    if endpoint:
        print(f"\n🎯 SUCCESS! Found working endpoint: {endpoint}")
        print(f"📋 Sample data structure:")
        print(json.dumps(data, indent=2)[:1000] + "..." if len(str(data)) > 1000 else json.dumps(data, indent=2))
    else:
        print(f"\n❌ No working vehicle compatibility endpoint found")
        print(f"💡 TecDoc RapidAPI might not provide vehicle compatibility data")
        print(f"💡 Need to find alternative approach for OEM-to-vehicle matching")
