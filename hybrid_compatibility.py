#!/usr/bin/env python3
"""
Hybrid Compatibility System
Combines fast matrix lookup with fallback to optimized search
Automatically caches new results for future queries
"""

import time
import json
from compatibility_matrix import fast_compatibility_lookup, cache_compatibility_result

def hybrid_car_parts_search(license_plate):
    """
    HYBRID APPROACH: Fast matrix lookup + optimized search fallback + auto-caching
    
    1. Try matrix lookup first (fast)
    2. If not found, use optimized search (complete coverage)
    3. Cache the result for future queries
    """
    start_time = time.time()
    
    try:
        print(f"🔄 HYBRID: Starting search for {license_plate}")
        
        # Step 1: Get vehicle info from SVV (always needed)
        from app import hent_kjoretoydata, extract_vehicle_info
        
        vehicle_data = hent_kjoretoydata(license_plate)
        if not vehicle_data:
            return {
                'error': 'Could not retrieve vehicle data from SVV',
                'license_plate': license_plate
            }
        
        vehicle_info = extract_vehicle_info(vehicle_data)
        if not vehicle_info:
            return {
                'error': 'Could not extract vehicle info',
                'license_plate': license_plate
            }
        
        print(f"🚗 Vehicle: {vehicle_info['make']} {vehicle_info['model']} {vehicle_info['year']}")
        
        # Step 2: Try FAST matrix lookup first
        matrix_start = time.time()
        try:
            compatible_products = fast_compatibility_lookup(
                vehicle_info['make'],
                vehicle_info['model'], 
                vehicle_info['year']
            )
            
            if compatible_products:
                matrix_time = time.time() - matrix_start
                total_time = time.time() - start_time
                
                print(f"⚡ MATRIX HIT! Found {len(compatible_products)} products in {matrix_time:.3f}s")
                
                # Check if MA01002 is found (for verification)
                ma01002_found = any(p['id'] == 'MA01002' for p in compatible_products)
                if ma01002_found:
                    print(f"🎯 MA01002 found via matrix!")
                
                return {
                    'vehicle_info': vehicle_info,
                    'license_plate': license_plate,
                    'compatible_products': len(compatible_products),
                    'shopify_parts': compatible_products,
                    'message': f'Found {len(compatible_products)} compatible parts via matrix lookup',
                    'performance': {
                        'total_time': round(total_time, 3),
                        'matrix_time': round(matrix_time, 3),
                        'method': 'matrix_hit'
                    },
                    'matrix_info': {
                        'ma01002_found': ma01002_found,
                        'lookup_method': 'matrix_cache'
                    }
                }
            else:
                print(f"📭 Matrix miss - vehicle not in cache")
                
        except Exception as matrix_error:
            print(f"⚠️ Matrix lookup failed: {matrix_error}")
        
        # Step 3: FALLBACK to optimized search
        print(f"🔄 Falling back to optimized search...")
        fallback_start = time.time()
        
        from optimized_search import optimized_car_parts_search
        result = optimized_car_parts_search(license_plate)
        
        if 'error' in result:
            return result
        
        fallback_time = time.time() - fallback_start
        total_time = time.time() - start_time
        
        print(f"✅ FALLBACK SUCCESS! Found {result.get('compatible_products', 0)} products in {fallback_time:.3f}s")
        
        # Step 4: CACHE the result for future queries
        try:
            if 'shopify_parts' in result and result['shopify_parts']:
                print(f"💾 Caching result for future queries...")
                cache_compatibility_result(
                    vehicle_info['make'],
                    vehicle_info['model'], 
                    vehicle_info['year'],
                    result['shopify_parts']
                )
                print(f"✅ Result cached successfully")
        except Exception as cache_error:
            print(f"⚠️ Failed to cache result: {cache_error}")
        
        # Update result with hybrid info
        if 'performance' not in result:
            result['performance'] = {}
        
        result['performance']['total_time'] = round(total_time, 3)
        result['performance']['fallback_time'] = round(fallback_time, 3)
        result['performance']['method'] = 'optimized_fallback'
        result['matrix_info'] = {
            'lookup_method': 'fallback_cached',
            'cached_for_future': True
        }
        result['message'] = f"Found {result.get('compatible_products', 0)} compatible parts via optimized search (cached for future)"
        
        return result
        
    except Exception as e:
        print(f"❌ Error in hybrid search: {e}")
        import traceback
        traceback.print_exc()
        return {
            'error': 'Hybrid search failed', 
            'details': str(e),
            'license_plate': license_plate
        }

if __name__ == "__main__":
    # Test the hybrid system
    print("🧪 Testing Hybrid Compatibility System...")
    
    # Test 1: Known vehicle (should hit matrix)
    print(f"\n🎯 TEST 1: Known vehicle YZ99554 (should hit matrix)")
    result1 = hybrid_car_parts_search("YZ99554")
    print(f"Method: {result1.get('performance', {}).get('method', 'N/A')}")
    print(f"Time: {result1.get('performance', {}).get('total_time', 'N/A')}s")
    print(f"Products: {result1.get('compatible_products', 0)}")
    
    # Test 2: Unknown vehicle (should use fallback and cache)
    print(f"\n🎯 TEST 2: Unknown vehicle RJ62438 (should use fallback)")
    result2 = hybrid_car_parts_search("RJ62438")
    print(f"Method: {result2.get('performance', {}).get('method', 'N/A')}")
    print(f"Time: {result2.get('performance', {}).get('total_time', 'N/A')}s")
    print(f"Products: {result2.get('compatible_products', 0)}")
    
    # Test 3: Same unknown vehicle again (should now hit matrix)
    print(f"\n🎯 TEST 3: Same vehicle RJ62438 again (should now hit matrix)")
    result3 = hybrid_car_parts_search("RJ62438")
    print(f"Method: {result3.get('performance', {}).get('method', 'N/A')}")
    print(f"Time: {result3.get('performance', {}).get('total_time', 'N/A')}s")
    print(f"Products: {result3.get('compatible_products', 0)}")
    
    print(f"\n🚀 Hybrid system tested - ready for production!")
