#!/usr/bin/env python3
"""
Test TecDoc API directly with ZT41818 VIN to see why it returns 0 OEMs
"""

import requests
import json

def create_tecdoc_vin_test_endpoint():
    """Create endpoint to test TecDoc API with specific VIN"""
    
    endpoint_code = '''
@app.route('/api/test/tecdoc_vin/<license_plate>', methods=['GET'])
def test_tecdoc_vin(license_plate):
    """Test TecDoc API directly with VIN from license plate"""
    from svv_client import hent_kjoretoydata
    from rapidapi_tecdoc import (
        extract_vin_from_svv, get_manufacturers, find_manufacturer_id,
        get_articles_by_vin, extract_oem_numbers_from_articles
    )
    import traceback
    
    result = {
        'license_plate': license_plate,
        'steps': {},
        'diagnosis': ''
    }
    
    try:
        # Step 1: Get VIN from SVV
        svv_data = hent_kjoretoydata(license_plate)
        if not svv_data:
            result['diagnosis'] = 'No SVV data'
            return jsonify(result)
        
        vin = extract_vin_from_svv(svv_data)
        if not vin:
            result['diagnosis'] = 'No VIN extracted'
            return jsonify(result)
        
        result['steps']['vin_extraction'] = {
            'success': True,
            'vin': vin
        }
        
        # Step 2: Get manufacturer ID for Nissan
        manufacturers_data = get_manufacturers()
        if not manufacturers_data:
            result['diagnosis'] = 'Failed to get manufacturers'
            return jsonify(result)
        
        manufacturers_list = manufacturers_data.get('manufacturers', [])
        manufacturer_id = find_manufacturer_id('NISSAN', manufacturers_list)
        if not manufacturer_id:
            result['diagnosis'] = 'Nissan manufacturer not found'
            return jsonify(result)
        
        result['steps']['manufacturer'] = {
            'success': True,
            'manufacturer_id': manufacturer_id
        }
        
        # Step 3: Test TecDoc VIN API for both product groups
        product_groups = [
            (100260, "Drivaksler"),
            (100270, "Mellomaksler")
        ]
        
        result['steps']['tecdoc_api_calls'] = []
        
        for product_group_id, group_name in product_groups:
            try:
                articles = get_articles_by_vin(vin, product_group_id, manufacturer_id)
                
                api_result = {
                    'product_group': group_name,
                    'product_group_id': product_group_id,
                    'success': articles is not None,
                    'articles_count': 0,
                    'oems_count': 0,
                    'sample_oems': []
                }
                
                if articles:
                    # Handle both dict and list formats
                    articles_list = articles.get('articles', []) if isinstance(articles, dict) else articles
                    api_result['articles_count'] = len(articles_list)
                    
                    if articles_list:
                        oems = extract_oem_numbers_from_articles({'articles': articles_list})
                        api_result['oems_count'] = len(oems)
                        api_result['sample_oems'] = oems[:10]  # First 10 OEMs
                
                result['steps']['tecdoc_api_calls'].append(api_result)
                
            except Exception as e:
                result['steps']['tecdoc_api_calls'].append({
                    'product_group': group_name,
                    'product_group_id': product_group_id,
                    'success': False,
                    'error': str(e)
                })
        
        # Summary and diagnosis
        total_oems = sum(call.get('oems_count', 0) for call in result['steps']['tecdoc_api_calls'])
        
        if total_oems > 0:
            result['diagnosis'] = f'SUCCESS: TecDoc API returned {total_oems} OEMs for VIN {vin}'
        else:
            successful_calls = [call for call in result['steps']['tecdoc_api_calls'] if call.get('success')]
            failed_calls = [call for call in result['steps']['tecdoc_api_calls'] if not call.get('success')]
            
            if failed_calls:
                result['diagnosis'] = f'TecDoc API calls failed for VIN {vin}'
            else:
                result['diagnosis'] = f'TecDoc API calls succeeded but returned 0 OEMs for VIN {vin}'
        
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
    print("🔍 CREATING TECDOC VIN TEST ENDPOINT")
    print("=" * 40)
    
    endpoint_code = create_tecdoc_vin_test_endpoint()
    
    print(f"\n🎯 This endpoint will:")
    print(f"   1. Extract VIN from ZT41818 (should be JN1TENT30U0217281)")
    print(f"   2. Get Nissan manufacturer ID from TecDoc")
    print(f"   3. Call TecDoc API with VIN for both product groups")
    print(f"   4. Show exact API response and OEM extraction")
    print(f"   5. Diagnose why TecDoc returns 0 OEMs")
    
    print(f"\n💡 Expected results:")
    print(f"   - VIN extraction: SUCCESS (already confirmed)")
    print(f"   - Manufacturer ID: Should find Nissan")
    print(f"   - TecDoc API calls: Should return articles/OEMs")
    print(f"   - If API calls fail: TecDoc API issue")
    print(f"   - If API calls succeed but 0 OEMs: OEM extraction issue")
