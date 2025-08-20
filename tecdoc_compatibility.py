#!/usr/bin/env python3
"""
Optimized TecDoc Compatibility Check
Fast verification that OEM numbers are actually compatible with specific vehicles
"""

import time
from typing import List, Dict, Set, Tuple

# Cache for compatibility results to avoid duplicate API calls
compatibility_cache = {}

def check_oem_vehicle_compatibility_batch(oem_numbers: List[str], vehicle_make: str, vehicle_model: str, vehicle_year: int) -> Dict[str, bool]:
    """
    OPTIMIZED: Check multiple OEM numbers for vehicle compatibility in batch
    Returns dict of {oem_number: is_compatible}
    """
    print(f"🔍 COMPATIBILITY CHECK: Verifying {len(oem_numbers)} OEMs for {vehicle_make} {vehicle_model} {vehicle_year}")
    
    # Create cache key for this vehicle
    vehicle_key = f"{vehicle_make}_{vehicle_model}_{vehicle_year}".upper()
    
    results = {}
    uncached_oems = []
    
    # Step 1: Check cache first (FAST)
    for oem in oem_numbers:
        cache_key = f"{oem}_{vehicle_key}"
        if cache_key in compatibility_cache:
            results[oem] = compatibility_cache[cache_key]
            print(f"✅ CACHE HIT: {oem} → {results[oem]}")
        else:
            uncached_oems.append(oem)
    
    if not uncached_oems:
        print(f"🚀 ALL CACHE HITS: {len(oem_numbers)} OEMs resolved from cache")
        return results
    
    print(f"📡 API CALLS NEEDED: {len(uncached_oems)} OEMs not in cache")
    
    # Step 2: Get vehicle-specific OEMs from TecDoc (what OEMs are actually valid for this vehicle)
    try:
        from rapidapi_tecdoc import get_oem_numbers_from_rapidapi_tecdoc
        
        print(f"📋 Getting valid OEMs for {vehicle_make} {vehicle_model} {vehicle_year}...")
        valid_oems_for_vehicle = get_oem_numbers_from_rapidapi_tecdoc(vehicle_make, vehicle_model, vehicle_year)
        
        if not valid_oems_for_vehicle:
            print(f"❌ TecDoc returned no valid OEMs for this vehicle")
            # Mark all uncached OEMs as incompatible
            for oem in uncached_oems:
                results[oem] = False
                cache_key = f"{oem}_{vehicle_key}"
                compatibility_cache[cache_key] = False
            return results
        
        # Convert to set for fast lookup
        valid_oems_set = set(oem.upper().strip() for oem in valid_oems_for_vehicle)
        print(f"✅ TecDoc returned {len(valid_oems_set)} valid OEMs for this vehicle")
        print(f"🔍 First 5 valid OEMs: {list(valid_oems_set)[:5]}")
        
        # Step 3: Check each uncached OEM against valid OEMs
        for oem in uncached_oems:
            oem_normalized = oem.upper().strip()
            
            # Direct match
            is_compatible = oem_normalized in valid_oems_set
            
            # Also check without A prefix (A2044102401 vs 2044102401)
            if not is_compatible and oem_normalized.startswith('A'):
                oem_without_a = oem_normalized[1:]
                is_compatible = oem_without_a in valid_oems_set
            
            # Also check with A prefix
            if not is_compatible and not oem_normalized.startswith('A'):
                oem_with_a = f"A{oem_normalized}"
                is_compatible = oem_with_a in valid_oems_set
            
            results[oem] = is_compatible
            
            # Cache the result
            cache_key = f"{oem}_{vehicle_key}"
            compatibility_cache[cache_key] = is_compatible
            
            status = "✅ COMPATIBLE" if is_compatible else "❌ INCOMPATIBLE"
            print(f"   {status}: {oem}")
    
    except Exception as e:
        print(f"❌ Error in compatibility check: {e}")
        # Mark all uncached OEMs as incompatible on error
        for oem in uncached_oems:
            results[oem] = False
            cache_key = f"{oem}_{vehicle_key}"
            compatibility_cache[cache_key] = False
    
    compatible_count = sum(1 for is_compat in results.values() if is_compat)
    print(f"🎯 COMPATIBILITY RESULTS: {compatible_count}/{len(oem_numbers)} OEMs are compatible")
    
    return results

def filter_products_by_compatibility(products: List[Dict], vehicle_make: str, vehicle_model: str, vehicle_year: int) -> List[Dict]:
    """
    Filter products to only include those with OEMs that are actually compatible with the vehicle
    """
    if not products:
        return []
    
    print(f"🔍 FILTERING {len(products)} products by TecDoc compatibility...")
    
    # Extract all unique OEM numbers from products
    all_oems = set()
    for product in products:
        matched_oem = product.get('matched_oem', '')
        if matched_oem:
            all_oems.add(matched_oem)
    
    if not all_oems:
        print(f"❌ No OEM numbers found in products")
        return []
    
    print(f"📋 Found {len(all_oems)} unique OEM numbers to check")
    
    # Check compatibility for all OEMs
    compatibility_results = check_oem_vehicle_compatibility_batch(
        list(all_oems), vehicle_make, vehicle_model, vehicle_year
    )
    
    # Filter products based on compatibility
    compatible_products = []
    for product in products:
        matched_oem = product.get('matched_oem', '')
        if matched_oem and compatibility_results.get(matched_oem, False):
            compatible_products.append(product)
            print(f"✅ COMPATIBLE: {product.get('title', '')} (OEM: {matched_oem})")
        else:
            print(f"❌ FILTERED OUT: {product.get('title', '')} (OEM: {matched_oem})")
    
    print(f"🎯 FILTERING COMPLETE: {len(compatible_products)}/{len(products)} products are truly compatible")
    
    return compatible_products

def get_compatibility_cache_stats():
    """Get statistics about the compatibility cache"""
    return {
        'total_entries': len(compatibility_cache),
        'cache_keys': list(compatibility_cache.keys())[:10]  # First 10 for debugging
    }

if __name__ == "__main__":
    # Test the compatibility check
    test_oems = ["A2044102401", "2043301500", "1K0407271AK"]
    test_vehicle = ("MERCEDES-BENZ", "GLK 220 CDI 4MATIC", 2010)
    
    print("🧪 TESTING COMPATIBILITY CHECK")
    print("=" * 50)
    
    results = check_oem_vehicle_compatibility_batch(test_oems, *test_vehicle)
    
    print(f"\n📊 TEST RESULTS:")
    for oem, is_compatible in results.items():
        status = "✅ Compatible" if is_compatible else "❌ Incompatible"
        print(f"   {oem}: {status}")
    
    print(f"\n💾 Cache stats: {get_compatibility_cache_stats()}")
