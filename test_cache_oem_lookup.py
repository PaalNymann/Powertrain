#!/usr/bin/env python3
"""
Test the new cache-based OEM lookup for all vehicles
"""

import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_cache_oem_lookup():
    """Test cache OEM lookup for different vehicles"""
    
    print("🧪 TESTING CACHE-BASED OEM LOOKUP")
    print("=" * 50)
    
    # Test vehicles
    test_vehicles = [
        ("YZ99554", "MERCEDES-BENZ", "GLK 220 CDI 4MATIC", "2010"),
        ("KH66644", "VOLVO", "V70", "2006"), 
        ("RJ62438", "VOLVO", "V40", "2012")
    ]
    
    try:
        from compatibility_matrix import get_oems_for_vehicle_from_cache
        
        for license_plate, make, model, year in test_vehicles:
            print(f"\n🚗 Testing {license_plate}: {make} {model} {year}")
            print("-" * 40)
            
            try:
                oem_numbers = get_oems_for_vehicle_from_cache(make, model, year)
                
                if oem_numbers:
                    print(f"✅ Found {len(oem_numbers)} OEM numbers")
                    print(f"🔍 First 5 OEMs: {oem_numbers[:5]}")
                    
                    # Test if we can find products with these OEMs
                    print(f"🛍️ Testing product matching...")
                    from optimized_search import search_products_by_oem_optimized
                    
                    total_products = 0
                    for oem in oem_numbers[:3]:  # Test first 3 OEMs only
                        products = search_products_by_oem_optimized(oem)
                        if products:
                            total_products += len(products)
                            print(f"   OEM {oem}: {len(products)} products")
                    
                    print(f"📊 Total products found: {total_products}")
                    
                else:
                    print(f"❌ No OEM numbers found in cache")
                    
            except Exception as e:
                print(f"❌ Error testing {license_plate}: {e}")
                import traceback
                traceback.print_exc()
    
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure compatibility_matrix.py and optimized_search.py are available")
    
    print(f"\n🏁 Cache OEM lookup test completed!")

if __name__ == "__main__":
    test_cache_oem_lookup()
