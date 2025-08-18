#!/usr/bin/env python3
"""
Fast Compatibility API
Production-ready endpoint using pre-computed compatibility matrix
"""

import time
from flask import jsonify
from compatibility_matrix import fast_compatibility_lookup

def fast_car_parts_search_api(license_plate):
    """
    PRODUCTION: Fast car parts search using pre-computed compatibility matrix
    This replaces the slow direct product testing with instant database lookup
    """
    start_time = time.time()
    
    try:
        print(f"🚀 FAST API: Starting search for {license_plate}")
        
        # Step 1: Get vehicle info from SVV (same as before)
        from app import hent_kjoretoydata, extract_vehicle_info
        
        step1_start = time.time()
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
        
        step1_time = time.time() - step1_start
        print(f"🚗 Vehicle: {vehicle_info['make']} {vehicle_info['model']} {vehicle_info['year']}")
        
        # Step 2: FAST lookup in compatibility matrix
        step2_start = time.time()
        compatible_products = fast_compatibility_lookup(
            vehicle_info['make'],
            vehicle_info['model'], 
            vehicle_info['year']
        )
        step2_time = time.time() - step2_start
        
        total_time = time.time() - start_time
        
        print(f"⚡ FAST API COMPLETED in {total_time:.3f}s")
        print(f"📊 Found {len(compatible_products)} compatible products")
        
        # Check if MA01002 is found (for verification)
        ma01002_found = any(p['id'] == 'MA01002' for p in compatible_products)
        if ma01002_found:
            print(f"🎯 MA01002 found in results!")
        
        return {
            'vehicle_info': vehicle_info,
            'license_plate': license_plate,
            'compatible_products': len(compatible_products),
            'shopify_parts': compatible_products,
            'message': f'Found {len(compatible_products)} compatible parts via fast matrix lookup',
            'performance': {
                'total_time': round(total_time, 3),
                'step1_time': round(step1_time, 3),
                'step2_time': round(step2_time, 3),
                'method': 'pre-computed_matrix'
            },
            'matrix_info': {
                'ma01002_found': ma01002_found,
                'lookup_method': 'compatibility_matrix'
            }
        }
        
    except Exception as e:
        print(f"❌ Error in fast API: {e}")
        import traceback
        traceback.print_exc()
        return {
            'error': 'Internal server error', 
            'details': str(e),
            'license_plate': license_plate
        }

if __name__ == "__main__":
    # Test the fast API
    print("🧪 Testing Fast Compatibility API...")
    
    # Test with YZ99554 to verify MA01002 is found quickly
    result = fast_car_parts_search_api("YZ99554")
    
    print(f"\n🎯 FAST API RESULT:")
    print(f"⏱️ Total time: {result.get('performance', {}).get('total_time', 'N/A')}s")
    print(f"📦 Products found: {result.get('compatible_products', 0)}")
    print(f"🎯 MA01002 found: {'✅ YES' if result.get('matrix_info', {}).get('ma01002_found') else '❌ NO'}")
    
    if 'shopify_parts' in result and result['shopify_parts']:
        print(f"\n📦 Found products:")
        for product in result['shopify_parts'][:5]:  # Show first 5
            print(f"   - {product['id']}: {product['title']}")
        if len(result['shopify_parts']) > 5:
            print(f"   ... and {len(result['shopify_parts']) - 5} more")
    
    print(f"\n🚀 Fast API ready for production integration!")
