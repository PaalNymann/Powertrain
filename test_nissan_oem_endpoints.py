#!/usr/bin/env python3
"""
Test Different OEM Search Endpoints for Nissan X-trail
Find which endpoints actually return OEMs for this vehicle
"""

import requests
import json
import time

def test_nissan_oem_endpoints():
    """Test various OEM endpoints for Nissan X-trail"""
    
    rapidapi_key = "48a6ede874mshe38f052cb6a6109p12916fjsn0d0c0912c5ed"
    base_url = "https://tecdoc-catalog.p.rapidapi.com"
    headers = {
        'x-rapidapi-host': 'tecdoc-catalog.p.rapidapi.com',
        'x-rapidapi-key': rapidapi_key
    }
    
    print("🔍 TESTING DIFFERENT OEM ENDPOINTS FOR NISSAN X-TRAIL")
    print("=" * 60)
    
    # Test different search terms
    search_terms = [
        "Nissan X-trail",
        "Nissan",
        "X-trail",
        "NISSAN",
        "X-TRAIL",
        "nissan x-trail",
        "Nissan X-Trail"
    ]
    
    # Test different endpoint patterns
    endpoint_patterns = [
        "/articles-oem/search/lang-id/4/article-oem-search-no/{}",
        "/articles/search/lang-id/4/article-search-no/{}",
        "/oem/search/{}",
        "/parts/search/{}",
        "/search/oem/{}",
        "/search/articles/{}",
        "/manufacturers/search/{}",
        "/vehicles/search/{}"
    ]
    
    found_results = []
    
    for term in search_terms:
        print(f"\n🔍 Testing search term: '{term}'")
        
        for pattern in endpoint_patterns:
            endpoint = pattern.format(term)
            url = f"{base_url}{endpoint}"
            
            try:
                print(f"   Trying: {endpoint}")
                response = requests.get(url, headers=headers, timeout=8)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data:  # Non-empty response
                        result_count = len(data) if isinstance(data, list) else 1
                        print(f"   ✅ SUCCESS: {result_count} results")
                        
                        found_results.append({
                            'term': term,
                            'endpoint': endpoint,
                            'count': result_count,
                            'sample': data[:2] if isinstance(data, list) else data
                        })
                        
                        # Show sample of what we found
                        if isinstance(data, list) and data:
                            first_item = data[0]
                            if isinstance(first_item, dict):
                                keys = list(first_item.keys())
                                print(f"      Sample keys: {keys[:5]}")
                        
                    else:
                        print(f"   ⚪ Empty response")
                        
                elif response.status_code == 404:
                    print(f"   ⚪ 404 Not Found")
                else:
                    print(f"   ❌ {response.status_code}")
                    
            except Exception as e:
                print(f"   ❌ Error: {str(e)[:50]}")
            
            time.sleep(0.1)  # Rate limiting
    
    print(f"\n📋 SUMMARY OF SUCCESSFUL ENDPOINTS:")
    print("=" * 60)
    
    if found_results:
        for result in found_results:
            print(f"✅ {result['endpoint']}")
            print(f"   Term: '{result['term']}'")
            print(f"   Count: {result['count']}")
            print(f"   Sample: {str(result['sample'])[:100]}...")
            print()
    else:
        print("❌ No successful endpoints found for Nissan X-trail OEM search")
        
        print(f"\n🔍 TRYING ALTERNATIVE APPROACHES:")
        
        # Try manufacturer lookup first
        print(f"\n1. Trying manufacturer lookup:")
        try:
            url = f"{base_url}/manufacturers"
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Manufacturers endpoint works: {len(data) if isinstance(data, list) else 'dict'}")
                
                # Look for Nissan
                if isinstance(data, list):
                    nissan_entries = [item for item in data if isinstance(item, dict) and 
                                    any('nissan' in str(v).lower() for v in item.values())]
                    if nissan_entries:
                        print(f"   🎯 Found Nissan entries: {nissan_entries[:2]}")
            else:
                print(f"   ❌ Manufacturers endpoint failed: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Manufacturers error: {e}")
        
        # Try vehicle lookup
        print(f"\n2. Trying vehicle lookup:")
        try:
            url = f"{base_url}/vehicles"
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Vehicles endpoint works: {len(data) if isinstance(data, list) else 'dict'}")
            else:
                print(f"   ❌ Vehicles endpoint failed: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Vehicles error: {e}")

if __name__ == "__main__":
    test_nissan_oem_endpoints()
