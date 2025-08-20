#!/usr/bin/env python3
"""
Test multi-product group TecDoc search locally
Test if searching multiple product groups gives more OEMs for VW Tiguan
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from rapidapi_tecdoc import get_oem_numbers_from_rapidapi_tecdoc

def test_multi_product_groups():
    """Test multi-product group search for VW Tiguan 2009"""
    
    print("🧪 TESTING MULTI-PRODUCT GROUP TECDOC SEARCH")
    print("=" * 60)
    
    # Test vehicle: KH66644 = VW Tiguan 2009
    brand = "VOLKSWAGEN"
    model = "TIGUAN"
    year = 2009
    
    print(f"🚗 Testing: {brand} {model} {year}")
    print()
    
    # Test the updated function
    try:
        oem_numbers = get_oem_numbers_from_rapidapi_tecdoc(brand, model, year)
        
        print(f"\n📊 FINAL RESULTS:")
        print(f"   Total OEM numbers found: {len(oem_numbers)}")
        
        if oem_numbers:
            print(f"   First 10 OEMs:")
            for i, oem in enumerate(oem_numbers[:10]):
                print(f"      {i+1}. {oem}")
            
            if len(oem_numbers) > 10:
                print(f"      ... and {len(oem_numbers) - 10} more")
        else:
            print(f"   ❌ No OEM numbers found!")
        
        # Expected result: Should be much more than 5 OEMs
        if len(oem_numbers) > 20:
            print(f"\n✅ SUCCESS: Found {len(oem_numbers)} OEMs (much better than 5!)")
        elif len(oem_numbers) > 5:
            print(f"\n🔄 IMPROVEMENT: Found {len(oem_numbers)} OEMs (better than 5, but could be more)")
        else:
            print(f"\n❌ STILL LOW: Only {len(oem_numbers)} OEMs found")
            
    except Exception as e:
        print(f"❌ Error testing multi-product groups: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_multi_product_groups()
