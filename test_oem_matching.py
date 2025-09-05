#!/usr/bin/env python3
"""
Test if TecDoc OEMs for ZT41818 match products in database
"""

import requests
import json

BACKEND_URL = "https://web-production-0809b.up.railway.app"

def test_tecdoc_oems_matching():
    """Test each TecDoc OEM against search function"""
    
    print("🔍 TESTING TECDOC OEMS MATCHING FOR ZT41818")
    print("=" * 50)
    
    # TecDoc OEMs found for ZT41818 (Nissan X-Trail 2006)
    tecdoc_oems = [
        "LX 236",
        "LXS 41/1", 
        "0 986 B03 903",
        "0 986 B03 511"
    ]
    
    print(f"🎯 Testing {len(tecdoc_oems)} TecDoc OEMs:")
    for i, oem in enumerate(tecdoc_oems):
        print(f"   {i+1}. {oem}")
    print()
    
    # Create test endpoint to call search_products_by_oem_optimized for each OEM
    endpoint_code = '''
@app.route('/api/test/search_oem/<oem_number>', methods=['GET'])
def test_search_oem(oem_number):
    """Test search_products_by_oem_optimized with specific OEM"""
    from optimized_search import search_products_by_oem_optimized
    import traceback
    
    result = {
        'oem': oem_number,
        'products_found': 0,
        'sample_products': [],
        'diagnosis': ''
    }
    
    try:
        products = search_products_by_oem_optimized(oem_number)
        
        if products:
            result['products_found'] = len(products)
            result['sample_products'] = products[:3]  # First 3 products
            result['diagnosis'] = f'SUCCESS: Found {len(products)} products for OEM {oem_number}'
        else:
            result['products_found'] = 0
            result['diagnosis'] = f'NO MATCH: OEM {oem_number} not found in database'
        
        return jsonify(result)
        
    except Exception as e:
        result['error'] = str(e)
        result['traceback'] = traceback.format_exc()
        return jsonify(result), 500
'''
    
    print("🔧 Add this endpoint to app.py to test OEM matching:")
    print(endpoint_code)
    
    print(f"\n🎯 Expected results:")
    print(f"   - If any TecDoc OEMs match products: Problem is in main search flow")
    print(f"   - If no TecDoc OEMs match products: Database lacks these OEMs")
    print(f"   - This will explain why ZT41818 returns 0 parts")
    
    print(f"\n💡 Key insight:")
    print(f"   TecDoc returns Bosch/Löbro OEMs (LX 236, etc.)")
    print(f"   Database may have Nissan OEMs (37000-8H310, etc.)")
    print(f"   If no cross-reference exists, no matching will occur")

if __name__ == "__main__":
    test_tecdoc_oems_matching()
