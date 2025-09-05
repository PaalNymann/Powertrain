#!/usr/bin/env python3
"""
Test what OEMs the cache system actually returns for ZT41818
and test them against search_products_by_oem_optimized()
"""

import requests
import json

BACKEND_URL = "https://web-production-0809b.up.railway.app"

def create_cache_oem_debug_endpoint():
    """Create a debug endpoint that shows cache OEMs for ZT41818"""
    
    print("🔧 CREATING CACHE OEM DEBUG ENDPOINT")
    print("=" * 40)
    
    endpoint_code = '''
@app.route('/api/debug/cache_oems/<license_plate>', methods=['GET'])
def debug_cache_oems(license_plate):
    """
    Debug endpoint to show what OEMs the cache system returns
    """
    from svv_client import hent_kjoretoydata
    from compatibility_matrix import get_oems_for_vehicle_from_cache
    from optimized_search import search_products_by_oem_optimized
    import traceback
    
    debug_info = {
        'license_plate': license_plate,
        'steps': {}
    }
    
    try:
        # Step 1: Get vehicle data
        vehicle_data = hent_kjoretoydata(license_plate)
        if not vehicle_data:
            return jsonify({'error': 'No vehicle data'})
        
        vehicle_info = extract_vehicle_info(vehicle_data)
        debug_info['vehicle_info'] = {
            'make': vehicle_info.get('make'),
            'model': vehicle_info.get('model'),
            'year': vehicle_info.get('year')
        }
        
        # Step 2: Get OEMs from cache
        try:
            cache_oems = get_oems_for_vehicle_from_cache(
                vehicle_info['make'], 
                vehicle_info['model'], 
                vehicle_info['year']
            )
            
            debug_info['cache_oems'] = {
                'count': len(cache_oems) if cache_oems else 0,
                'oems': cache_oems[:20] if cache_oems else []  # First 20 for inspection
            }
            
        except Exception as e:
            debug_info['cache_oems'] = {
                'error': str(e),
                'traceback': traceback.format_exc()
            }
            return jsonify(debug_info)
        
        # Step 3: Test each cache OEM against search function
        if cache_oems:
            search_results = []
            for i, oem in enumerate(cache_oems[:5]):  # Test first 5
                try:
                    products = search_products_by_oem_optimized(oem)
                    search_results.append({
                        'oem': oem,
                        'products_found': len(products) if products else 0,
                        'sample_products': [p.get('title', 'Unknown')[:50] for p in (products[:2] if products else [])]
                    })
                except Exception as e:
                    search_results.append({
                        'oem': oem,
                        'error': str(e)
                    })
            
            debug_info['search_results'] = search_results
        
        # Summary
        debug_info['summary'] = {
            'cache_oems_found': len(cache_oems) if cache_oems else 0,
            'search_matches': sum(1 for r in debug_info.get('search_results', []) if r.get('products_found', 0) > 0),
            'diagnosis': 'Unknown'
        }
        
        if debug_info['summary']['cache_oems_found'] == 0:
            debug_info['summary']['diagnosis'] = 'Cache returns no OEMs'
        elif debug_info['summary']['search_matches'] == 0:
            debug_info['summary']['diagnosis'] = 'Cache OEMs do not match database products'
        else:
            debug_info['summary']['diagnosis'] = 'Cache OEMs match some database products'
        
        return jsonify(debug_info)
        
    except Exception as e:
        debug_info['error'] = str(e)
        debug_info['traceback'] = traceback.format_exc()
        return jsonify(debug_info), 500
'''
    
    print("🔧 Add this endpoint to app.py:")
    print(endpoint_code)
    
    return endpoint_code

def test_manual_oem_search():
    """Test some known OEMs manually against the backend"""
    
    print(f"\n🔍 TESTING KNOWN OEMS MANUALLY")
    print("=" * 35)
    
    # Known customer-verified Nissan OEMs for MA18002
    test_oems = [
        "370008H310",
        "370008H510", 
        "370008H800",
        "37000-8H310",
        "37000-8H510",
        "37000-8H800"
    ]
    
    print(f"🎯 Testing customer-verified Nissan OEMs:")
    for oem in test_oems:
        print(f"   - {oem}")
    
    print(f"\n💡 These should be found in Original_nummer metafields")
    print(f"💡 If MA18002 is synced, it should appear in results")
    print(f"💡 Need to test these OEMs against search_products_by_oem_optimized()")

def analyze_oem_format_differences():
    """Analyze potential OEM format differences"""
    
    print(f"\n🔍 ANALYZING OEM FORMAT DIFFERENCES")
    print("=" * 40)
    
    print(f"📊 Potential Issues:")
    print(f"   1. Cache OEMs vs Database OEMs format mismatch")
    print(f"   2. Case sensitivity (UPPER vs lower)")
    print(f"   3. Hyphen/space differences (37000-8H310 vs 370008H310)")
    print(f"   4. Leading/trailing whitespace")
    print(f"   5. Comma-separated list parsing issues")
    
    print(f"\n🔧 Debug Strategy:")
    print(f"   1. Get exact OEMs from cache for ZT41818")
    print(f"   2. Test each OEM against search_products_by_oem_optimized()")
    print(f"   3. Check SQL LIKE patterns and normalization")
    print(f"   4. Compare with working vehicle (YZ99554)")
    
    print(f"\n💡 The search_products_by_oem_optimized() function has:")
    print(f"   - Comprehensive OEM variation logic (lines 383-395)")
    print(f"   - Multiple SQL LIKE patterns (lines 411-426)")
    print(f"   - Extensive debug logging")
    print(f"   - But it may not be receiving the right OEMs from cache")

if __name__ == "__main__":
    print("🔍 CACHE OEM EXTRACTION AND TESTING")
    print("=" * 40)
    
    # Create debug endpoint code
    endpoint_code = create_cache_oem_debug_endpoint()
    
    # Test manual OEMs
    test_manual_oem_search()
    
    # Analyze format differences
    analyze_oem_format_differences()
    
    print(f"\n🎯 NEXT STEPS:")
    print(f"1. Add cache OEM debug endpoint to app.py")
    print(f"2. Test it with ZT41818 to see exact cache OEMs")
    print(f"3. Debug why these OEMs don't match database products")
    print(f"4. Fix OEM normalization or SQL matching logic")
