#!/usr/bin/env python3
"""
Debug VIN-based TecDoc API calls for ZT41818
"""

import requests
import json

# TecDoc RapidAPI credentials
BASE_URL = "https://tecdoc-catalog.p.rapidapi.com"
HEADERS = {
    'x-rapidapi-host': 'tecdoc-catalog.p.rapidapi.com',
    'x-rapidapi-key': '48a6ede874mshe38f052cb6a6109p12916fjsn0d0c0912c5ed'
}

LANG_ID = 4  # English
COUNTRY_ID = 62  # Norway
TYPE_ID = 1  # Passenger cars

def test_vin_endpoints():
    """Test different VIN-based TecDoc endpoints"""
    vin = "JN1TENT30U0217281"  # ZT41818 VIN
    
    print(f"🧪 Testing VIN-based TecDoc endpoints for: {vin}")
    print("=" * 60)
    
    # Test common VIN endpoint patterns
    test_urls = [
        # Pattern 1: VIN in path with product group
        f"{BASE_URL}/articles/list/vin-no/{vin}/product-group-id/100260/lang-id/{LANG_ID}/country-filter-id/{COUNTRY_ID}/type-id/{TYPE_ID}",
        
        # Pattern 2: VIN as query parameter
        f"{BASE_URL}/articles/list/product-group-id/100260/lang-id/{LANG_ID}/country-filter-id/{COUNTRY_ID}/type-id/{TYPE_ID}?vin={vin}",
        
        # Pattern 3: VIN with chassis-no
        f"{BASE_URL}/articles/list/chassis-no/{vin}/product-group-id/100260/lang-id/{LANG_ID}/country-filter-id/{COUNTRY_ID}/type-id/{TYPE_ID}",
        
        # Pattern 4: VIN decode endpoint
        f"{BASE_URL}/vehicles/decode/vin/{vin}",
        
        # Pattern 5: VIN lookup endpoint
        f"{BASE_URL}/vehicles/lookup/vin/{vin}",
        
        # Pattern 6: VIN search endpoint
        f"{BASE_URL}/vehicles/search/vin/{vin}",
        
        # Pattern 7: Articles by VIN
        f"{BASE_URL}/articles/by-vin/{vin}/product-group/{100260}",
        
        # Pattern 8: Vehicle info by VIN
        f"{BASE_URL}/vehicle-info/vin/{vin}",
        
        # Pattern 9: VIN with underscores
        f"{BASE_URL}/articles_list/vin/{vin}/product_group_id/100260/lang_id/{LANG_ID}",
        
        # Pattern 10: POST endpoint with VIN in body (test with GET first)
        f"{BASE_URL}/articles/search/vin",
    ]
    
    for i, url in enumerate(test_urls, 1):
        print(f"🔍 Test {i}: {url}")
        try:
            response = requests.get(url, headers=HEADERS, timeout=10)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if isinstance(data, dict):
                        articles = data.get('articles', [])
                        count = data.get('countArticles', len(articles))
                        print(f"   ✅ SUCCESS! Articles found: {count}")
                        if articles:
                            print(f"   First article: {articles[0]}")
                        return url  # Return successful URL
                    else:
                        print(f"   Data: {str(data)[:100]}")
                except:
                    print(f"   Raw response: {response.text[:100]}")
            elif response.status_code == 404:
                print(f"   ❌ Endpoint not found")
            elif response.status_code == 400:
                print(f"   ⚠️ Bad request - might need different parameters")
                print(f"   Error: {response.text[:100]}")
            else:
                print(f"   Status {response.status_code}: {response.text[:100]}")
                
        except Exception as e:
            print(f"   Exception: {e}")
        
        print()
    
    print("❌ No working VIN endpoint found")
    return None

if __name__ == "__main__":
    test_vin_endpoints()
