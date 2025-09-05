#!/usr/bin/env python3
"""
Test TecDoc endpoints directly to see if VIN-based search works
"""

import requests
import json

def create_tecdoc_endpoint_test():
    """Create endpoint to test TecDoc endpoints directly"""
    
    endpoint_code = '''
@app.route('/api/test/tecdoc_endpoints/<license_plate>', methods=['GET'])
def test_tecdoc_endpoints(license_plate):
    """Test different TecDoc endpoints to find working VIN search"""
    from svv_client import hent_kjoretoydata
    from rapidapi_tecdoc import extract_vin_from_svv
    import requests
    import traceback
    
    # TecDoc Configuration
    RAPIDAPI_KEY = "48a6ede874mshe38f052cb6a6109p12916fjsn0d0c0912c5ed"
    BASE_URL = "https://tecdoc-catalog.p.rapidapi.com"
    HEADERS = {
        'x-rapidapi-host': 'tecdoc-catalog.p.rapidapi.com',
        'x-rapidapi-key': RAPIDAPI_KEY
    }
    
    result = {
        'license_plate': license_plate,
        'vin': '',
        'endpoint_tests': [],
        'diagnosis': ''
    }
    
    try:
        # Get VIN
        svv_data = hent_kjoretoydata(license_plate)
        if not svv_data:
            result['diagnosis'] = 'No SVV data'
            return jsonify(result)
        
        vin = extract_vin_from_svv(svv_data)
        if not vin:
            result['diagnosis'] = 'No VIN extracted'
            return jsonify(result)
        
        result['vin'] = vin
        
        # Test different TecDoc endpoints
        manufacturer_id = 80  # Nissan
        product_group_id = 100260  # Drivaksler
        lang_id = 4  # English
        country_id = 62  # Germany
        type_id = 1  # Automobile
        
        endpoints_to_test = [
            {
                'name': 'VIN Articles List (Current)',
                'url': f"{BASE_URL}/articles/list/vin/{vin}/product-group-id/{product_group_id}/manufacturer-id/{manufacturer_id}/lang-id/{lang_id}/country-filter-id/{country_id}/type-id/{type_id}"
            },
            {
                'name': 'VIN Articles Alternative',
                'url': f"{BASE_URL}/articles/vin/{vin}/product-group/{product_group_id}"
            },
            {
                'name': 'VIN Search Direct',
                'url': f"{BASE_URL}/vin/{vin}/articles"
            },
            {
                'name': 'Articles by VIN Simple',
                'url': f"{BASE_URL}/articles/search/vin/{vin}"
            }
        ]
        
        for endpoint in endpoints_to_test:
            test_result = {
                'name': endpoint['name'],
                'url': endpoint['url'],
                'status_code': 0,
                'success': False,
                'articles_count': 0,
                'response_keys': [],
                'error': ''
            }
            
            try:
                response = requests.get(endpoint['url'], headers=HEADERS, timeout=30)
                test_result['status_code'] = response.status_code
                
                if response.status_code == 200:
                    data = response.json()
                    test_result['success'] = True
                    test_result['response_keys'] = list(data.keys()) if isinstance(data, dict) else ['array']
                    
                    # Count articles
                    if isinstance(data, dict):
                        articles = data.get('articles', [])
                        test_result['articles_count'] = len(articles)
                    elif isinstance(data, list):
                        test_result['articles_count'] = len(data)
                else:
                    test_result['error'] = response.text[:200]  # First 200 chars
                    
            except Exception as e:
                test_result['error'] = str(e)
            
            result['endpoint_tests'].append(test_result)
        
        # Diagnosis
        successful_tests = [t for t in result['endpoint_tests'] if t['success']]
        tests_with_articles = [t for t in successful_tests if t['articles_count'] > 0]
        
        if tests_with_articles:
            result['diagnosis'] = f"SUCCESS: Found {len(tests_with_articles)} working endpoints with articles"
        elif successful_tests:
            result['diagnosis'] = f"PARTIAL: {len(successful_tests)} endpoints work but return 0 articles"
        else:
            result['diagnosis'] = "FAILURE: No TecDoc endpoints work for this VIN"
        
        return jsonify(result)
        
    except Exception as e:
        result['error'] = str(e)
        result['traceback'] = traceback.format_exc()
        return jsonify(result), 500
'''
    
    print("🔧 Add this endpoint to app.py:")
    print(endpoint_code)
    return endpoint_code

if __name__ == "__main__":
    print("🔍 CREATING TECDOC ENDPOINT TEST")
    print("=" * 35)
    
    endpoint_code = create_tecdoc_endpoint_test()
    
    print(f"\n🎯 This will test different TecDoc VIN endpoints:")
    print(f"   1. Current VIN articles list endpoint")
    print(f"   2. Alternative VIN articles endpoint") 
    print(f"   3. Direct VIN search endpoint")
    print(f"   4. Simple VIN articles search")
    print(f"\n💡 Goal: Find which TecDoc endpoint actually returns articles for VIN JN1TENT30U0217281")
