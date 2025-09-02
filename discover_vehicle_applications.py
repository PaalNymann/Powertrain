#!/usr/bin/env python3
"""
Comprehensive search for TecDoc vehicle applications endpoints
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

def test_comprehensive_endpoints():
    """Test comprehensive list of potential TecDoc endpoints"""
    
    print("🔍 COMPREHENSIVE TECDOC ENDPOINT DISCOVERY")
    print("=" * 60)
    
    article_id = "261965"  # Known Nissan article ID
    manufacturer_id = "184"  # Nissan
    vehicle_id = "19942"  # Known vehicle ID
    
    # Comprehensive list of potential endpoints based on TecDoc patterns
    test_endpoints = [
        # Vehicle Applications (most likely patterns)
        f"/vehicle-applications/list/article-id/{article_id}/lang-id/{LANG_ID}/country-filter-id/{COUNTRY_ID}/type-id/{TYPE_ID}",
        f"/applications/vehicle/article-id/{article_id}/lang-id/{LANG_ID}/country-filter-id/{COUNTRY_ID}/type-id/{TYPE_ID}",
        f"/articles/applications/article-id/{article_id}/lang-id/{LANG_ID}/country-filter-id/{COUNTRY_ID}/type-id/{TYPE_ID}",
        f"/vehicle/applications/article-id/{article_id}/lang-id/{LANG_ID}/country-filter-id/{COUNTRY_ID}/type-id/{TYPE_ID}",
        
        # Alternative patterns with different parameter orders
        f"/applications/list/article-id/{article_id}/lang-id/{LANG_ID}/country-filter-id/{COUNTRY_ID}/type-id/{TYPE_ID}",
        f"/applications/article/{article_id}/lang-id/{LANG_ID}/country-filter-id/{COUNTRY_ID}/type-id/{TYPE_ID}",
        f"/article-applications/list/article-id/{article_id}/lang-id/{LANG_ID}/country-filter-id/{COUNTRY_ID}/type-id/{TYPE_ID}",
        f"/article-vehicle-applications/list/article-id/{article_id}/lang-id/{LANG_ID}/country-filter-id/{COUNTRY_ID}/type-id/{TYPE_ID}",
        
        # Shorter patterns
        f"/applications/{article_id}/lang-id/{LANG_ID}",
        f"/vehicle-applications/{article_id}/lang-id/{LANG_ID}",
        f"/article-applications/{article_id}/lang-id/{LANG_ID}",
        
        # Different naming conventions
        f"/vehicleApplications/list/articleId/{article_id}/langId/{LANG_ID}/countryFilterId/{COUNTRY_ID}/typeId/{TYPE_ID}",
        f"/articleApplications/list/articleId/{article_id}/langId/{LANG_ID}/countryFilterId/{COUNTRY_ID}/typeId/{TYPE_ID}",
        
        # With manufacturer context
        f"/applications/list/article-id/{article_id}/manufacturer-id/{manufacturer_id}/lang-id/{LANG_ID}/country-filter-id/{COUNTRY_ID}/type-id/{TYPE_ID}",
        f"/vehicle-applications/list/article-id/{article_id}/manufacturer-id/{manufacturer_id}/lang-id/{LANG_ID}/country-filter-id/{COUNTRY_ID}/type-id/{TYPE_ID}",
        
        # Reverse lookup - from vehicle to articles
        f"/articles/list/vehicle-applications/vehicle-id/{vehicle_id}/lang-id/{LANG_ID}/country-filter-id/{COUNTRY_ID}/type-id/{TYPE_ID}",
        f"/vehicle-applications/articles/vehicle-id/{vehicle_id}/lang-id/{LANG_ID}/country-filter-id/{COUNTRY_ID}/type-id/{TYPE_ID}",
        
        # Generic search patterns
        f"/search/applications/article-id/{article_id}/lang-id/{LANG_ID}",
        f"/search/vehicle-applications/article-id/{article_id}/lang-id/{LANG_ID}",
        
        # Alternative structures
        f"/catalog/applications/article/{article_id}/lang/{LANG_ID}/country/{COUNTRY_ID}/type/{TYPE_ID}",
        f"/tecdoc/applications/article/{article_id}/lang/{LANG_ID}/country/{COUNTRY_ID}/type/{TYPE_ID}",
        
        # Without lang/country parameters (simpler)
        f"/applications/list/article-id/{article_id}",
        f"/vehicle-applications/list/article-id/{article_id}",
        f"/article-applications/list/article-id/{article_id}",
        f"/applications/{article_id}",
        f"/vehicle-applications/{article_id}",
        
        # POST endpoints (test with GET first)
        f"/applications/search",
        f"/vehicle-applications/search",
        f"/article-applications/search",
    ]
    
    successful_endpoints = []
    
    for i, endpoint in enumerate(test_endpoints, 1):
        print(f"\n🔍 Test {i:2d}: {endpoint}")
        url = BASE_URL + endpoint
        
        try:
            response = requests.get(url, headers=HEADERS, timeout=8)
            status = response.status_code
            
            if status == 200:
                try:
                    data = response.json()
                    
                    # Analyze response structure
                    if isinstance(data, dict):
                        keys = list(data.keys())
                        print(f"   ✅ SUCCESS! Dict with keys: {keys}")
                        
                        # Look for vehicle/application data
                        vehicle_data_found = False
                        for key, value in data.items():
                            if isinstance(value, list) and value:
                                print(f"   📋 {key}: {len(value)} items")
                                if len(value) > 0:
                                    first_item = value[0]
                                    if isinstance(first_item, dict):
                                        item_keys = list(first_item.keys())
                                        print(f"      First item keys: {item_keys}")
                                        # Check for vehicle-related keys
                                        if any(term in str(item_keys).lower() for term in ['vehicle', 'model', 'manufacturer', 'car', 'brand']):
                                            vehicle_data_found = True
                                            print(f"      🎯 VEHICLE DATA FOUND!")
                            elif key.lower() in ['vehicles', 'applications', 'cars', 'models']:
                                vehicle_data_found = True
                                print(f"   🎯 VEHICLE-RELATED KEY: {key} = {value}")
                        
                        if vehicle_data_found:
                            successful_endpoints.append((endpoint, data))
                            print(f"   🌟 POTENTIAL MATCH - saving for detailed analysis")
                            
                    elif isinstance(data, list):
                        print(f"   ✅ SUCCESS! List with {len(data)} items")
                        if data:
                            first_item = data[0]
                            print(f"   First item: {first_item}")
                            if isinstance(first_item, dict):
                                item_keys = list(first_item.keys())
                                if any(term in str(item_keys).lower() for term in ['vehicle', 'model', 'manufacturer', 'car', 'brand']):
                                    successful_endpoints.append((endpoint, data))
                                    print(f"   🌟 POTENTIAL MATCH - saving for detailed analysis")
                    else:
                        print(f"   Data type: {type(data)} = {data}")
                        
                except Exception as e:
                    print(f"   Raw response: {response.text[:150]}...")
                    
            elif status == 404:
                print(f"   ❌ Not found")
            elif status == 400:
                print(f"   ⚠️ Bad request: {response.text[:100]}")
            elif status == 403:
                print(f"   🔒 Forbidden")
            elif status == 500:
                print(f"   💥 Server error")
            else:
                print(f"   Status {status}: {response.text[:100]}")
                
        except requests.exceptions.Timeout:
            print(f"   ⏰ Timeout")
        except Exception as e:
            print(f"   ❌ Exception: {e}")
    
    # Summary
    print(f"\n" + "=" * 60)
    print(f"🎯 DISCOVERY RESULTS")
    print(f"=" * 60)
    
    if successful_endpoints:
        print(f"✅ Found {len(successful_endpoints)} potentially working endpoints:")
        for i, (endpoint, data) in enumerate(successful_endpoints, 1):
            print(f"\n{i}. {endpoint}")
            print(f"   Data preview: {str(data)[:200]}...")
            
        # Detailed analysis of first successful endpoint
        if successful_endpoints:
            print(f"\n📋 DETAILED ANALYSIS OF FIRST SUCCESSFUL ENDPOINT:")
            endpoint, data = successful_endpoints[0]
            print(f"Endpoint: {endpoint}")
            print(f"Full data structure:")
            print(json.dumps(data, indent=2))
            
    else:
        print(f"❌ No working vehicle applications endpoints found")
        print(f"💡 TecDoc RapidAPI might use different naming or require different parameters")

if __name__ == "__main__":
    test_comprehensive_endpoints()
