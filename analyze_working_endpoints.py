#!/usr/bin/env python3
"""
Analyze working TecDoc endpoints to understand the URL pattern
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

def analyze_working_endpoints():
    """Analyze working endpoints to understand the pattern"""
    
    print("🔍 ANALYZING WORKING TECDOC ENDPOINTS")
    print("=" * 50)
    
    # Known working endpoints from our existing code
    working_endpoints = [
        f"/manufacturers/list/lang-id/{LANG_ID}/country-filter-id/{COUNTRY_ID}/type-id/{TYPE_ID}",
        f"/models/list/manufacturer-id/184/lang-id/{LANG_ID}/country-filter-id/{COUNTRY_ID}/type-id/{TYPE_ID}",
        f"/articles/list/vehicle-id/19942/product-group-id/100260/manufacturer-id/184/lang-id/{LANG_ID}/country-filter-id/{COUNTRY_ID}/type-id/{TYPE_ID}",
        f"/articles/details/261965/lang-id/{LANG_ID}/country-filter-id/{COUNTRY_ID}",
        f"/articles-oem/search/lang-id/{LANG_ID}/article-oem-search-no/370008H310",
    ]
    
    print("✅ Testing known working endpoints to understand pattern:")
    
    for endpoint in working_endpoints:
        print(f"\n🔍 Testing: {endpoint}")
        url = BASE_URL + endpoint
        
        try:
            response = requests.get(url, headers=HEADERS, timeout=10)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ SUCCESS!")
                
                # Analyze structure
                if isinstance(data, dict):
                    keys = list(data.keys())
                    print(f"   Keys: {keys}")
                    
                    # Look for any vehicle/application related data
                    for key, value in data.items():
                        if isinstance(value, list) and value:
                            print(f"   {key}: {len(value)} items")
                            if len(value) > 0 and isinstance(value[0], dict):
                                item_keys = list(value[0].keys())
                                print(f"      Sample item keys: {item_keys}")
                                
                                # Check for vehicle-related keys in the data
                                vehicle_keys = [k for k in item_keys if any(term in k.lower() for term in ['vehicle', 'model', 'manufacturer', 'car', 'brand', 'application'])]
                                if vehicle_keys:
                                    print(f"      🎯 Vehicle-related keys found: {vehicle_keys}")
                        else:
                            print(f"   {key}: {value}")
                            
                elif isinstance(data, list):
                    print(f"   List with {len(data)} items")
                    if data and isinstance(data[0], dict):
                        item_keys = list(data[0].keys())
                        print(f"   Sample item keys: {item_keys}")
                        
            else:
                print(f"   ❌ Failed: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Exception: {e}")
    
    # Now try some variations based on the working pattern
    print(f"\n🔍 TRYING VARIATIONS BASED ON WORKING PATTERNS:")
    
    # Pattern analysis: working endpoints use specific structures
    # Let's try some logical variations
    
    variation_endpoints = [
        # Based on articles/list pattern - maybe there's a vehicles/list?
        f"/vehicles/list/article-id/261965/lang-id/{LANG_ID}/country-filter-id/{COUNTRY_ID}/type-id/{TYPE_ID}",
        
        # Based on articles-oem pattern - maybe there's article-vehicles?
        f"/article-vehicles/search/lang-id/{LANG_ID}/article-id/261965",
        f"/articles-vehicles/list/lang-id/{LANG_ID}/article-id/261965",
        
        # Try with different parameter order like articles/details
        f"/applications/list/261965/lang-id/{LANG_ID}/country-filter-id/{COUNTRY_ID}",
        f"/vehicles/list/261965/lang-id/{LANG_ID}/country-filter-id/{COUNTRY_ID}",
        
        # Maybe it's under a different main category
        f"/catalog/vehicles/list/article-id/261965/lang-id/{LANG_ID}/country-filter-id/{COUNTRY_ID}/type-id/{TYPE_ID}",
        f"/parts/vehicles/list/article-id/261965/lang-id/{LANG_ID}/country-filter-id/{COUNTRY_ID}/type-id/{TYPE_ID}",
        
        # Try POST endpoints that might exist
        f"/vehicles/search",
        f"/applications/search",
        f"/compatibility/search",
    ]
    
    for endpoint in variation_endpoints:
        print(f"\n🔍 Variation: {endpoint}")
        url = BASE_URL + endpoint
        
        try:
            response = requests.get(url, headers=HEADERS, timeout=8)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                print(f"   🎯 FOUND WORKING VARIATION!")
                data = response.json()
                print(f"   Data structure: {type(data)}")
                if isinstance(data, dict):
                    print(f"   Keys: {list(data.keys())}")
                elif isinstance(data, list):
                    print(f"   List length: {len(data)}")
                    if data:
                        print(f"   First item: {data[0]}")
                        
            elif response.status_code == 404:
                print(f"   ❌ Not found")
            elif response.status_code == 400:
                print(f"   ⚠️ Bad request - might need POST or different params")
            else:
                print(f"   Status {response.status_code}")
                
        except Exception as e:
            print(f"   Exception: {e}")
    
    print(f"\n💡 CONCLUSION:")
    print(f"If no vehicle applications endpoints are found, TecDoc RapidAPI might:")
    print(f"1. Not provide vehicle compatibility data")
    print(f"2. Require a different API subscription level")
    print(f"3. Use POST requests with specific payloads")
    print(f"4. Have vehicle data embedded in other endpoints we haven't checked")

if __name__ == "__main__":
    analyze_working_endpoints()
