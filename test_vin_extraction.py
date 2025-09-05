#!/usr/bin/env python3
"""
Test VIN extraction for ZT41818 to see if the problem is in VIN extraction or TecDoc API call
"""

import requests
import json

def test_vin_extraction():
    """Test VIN extraction for ZT41818"""
    
    print("🔍 TESTING VIN EXTRACTION FOR ZT41818")
    print("=" * 40)
    
    # Create a simple test endpoint to check VIN extraction
    endpoint_code = '''
@app.route('/api/test/vin_extraction/<license_plate>', methods=['GET'])
def test_vin_extraction(license_plate):
    """Test VIN extraction from SVV data"""
    from svv_client import hent_kjoretoydata
    from rapidapi_tecdoc import extract_vin_from_svv, extract_engine_code_from_svv, extract_engine_size_from_svv
    import traceback
    
    result = {
        'license_plate': license_plate,
        'svv_data': {},
        'extracted_info': {},
        'diagnosis': ''
    }
    
    try:
        # Get SVV data
        svv_data = hent_kjoretoydata(license_plate)
        if not svv_data:
            result['diagnosis'] = 'No SVV data found'
            return jsonify(result)
        
        # Show relevant parts of SVV data structure
        if 'kjoretoydataListe' in svv_data and svv_data['kjoretoydataListe']:
            kjoretoydata = svv_data['kjoretoydataListe'][0]
            kjoretoy_id = kjoretoydata.get('kjoretoyId', {})
            
            result['svv_data'] = {
                'has_kjoretoydataListe': True,
                'kjoretoyId_keys': list(kjoretoy_id.keys()),
                'understellsnummer': kjoretoy_id.get('understellsnummer', 'NOT FOUND'),
                'kjennemerke': kjoretoy_id.get('kjennemerke', 'NOT FOUND')
            }
        
        # Extract VIN and other info
        vin = extract_vin_from_svv(svv_data)
        engine_code = extract_engine_code_from_svv(svv_data)
        engine_size = extract_engine_size_from_svv(svv_data)
        
        result['extracted_info'] = {
            'vin': vin,
            'engine_code': engine_code,
            'engine_size': engine_size
        }
        
        # Diagnosis
        if vin:
            result['diagnosis'] = f'VIN extracted successfully: {vin}'
        else:
            result['diagnosis'] = 'VIN extraction failed - check SVV data structure'
        
        return jsonify(result)
        
    except Exception as e:
        result['error'] = str(e)
        result['traceback'] = traceback.format_exc()
        return jsonify(result), 500
'''
    
    print("🔧 Add this endpoint to app.py to test VIN extraction:")
    print(endpoint_code)
    
    print(f"\n🎯 This will show:")
    print(f"   1. SVV data structure for ZT41818")
    print(f"   2. Whether VIN (understellsnummer) exists")
    print(f"   3. Extracted VIN, engine code, engine size")
    print(f"   4. Diagnosis of extraction success/failure")
    
    print(f"\n💡 Expected for ZT41818:")
    print(f"   - Should have understellsnummer (VIN)")
    print(f"   - VIN should be extracted successfully")
    print(f"   - If VIN is empty, that's why TecDoc returns 0 OEMs")

if __name__ == "__main__":
    test_vin_extraction()
