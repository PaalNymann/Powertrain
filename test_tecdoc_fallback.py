#!/usr/bin/env python3
"""
Test TecDoc fallback function directly
"""

import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_tecdoc_fallback():
    """Test TecDoc fallback for our problem vehicles"""
    
    print("🧪 TESTING TECDOC FALLBACK DIRECTLY")
    print("=" * 50)
    
    test_vehicles = [
        ("MERCEDES-BENZ", "GLK 220 CDI 4MATIC", 2010),
        ("VOLKSWAGEN", "TIGUAN", 2009),
        ("VOLVO", "V70", 2006)
    ]
    
    try:
        from rapidapi_tecdoc import get_oem_numbers_from_rapidapi_tecdoc
        print("✅ Successfully imported TecDoc module")
        
        for brand, model, year in test_vehicles:
            print(f"\n🚗 Testing {brand} {model} {year}:")
            print("-" * 40)
            
            try:
                oem_numbers = get_oem_numbers_from_rapidapi_tecdoc(brand, model, year)
                
                if oem_numbers:
                    print(f"✅ TecDoc returned {len(oem_numbers)} OEM numbers")
                    print(f"🔍 First 5 OEMs: {oem_numbers[:5]}")
                else:
                    print(f"❌ TecDoc returned no OEM numbers")
                    
            except Exception as e:
                print(f"❌ TecDoc error: {e}")
                import traceback
                traceback.print_exc()
    
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("TecDoc module not available - this explains why fallback fails!")
        return
    
    print(f"\n🎯 FALLBACK TEST RESULTS:")
    print("If TecDoc returns OEMs here but not in production, the problem is:")
    print("1. TecDoc fallback is not being called in production")
    print("2. Environment/API key issues in production")
    print("3. Import/module issues in production")

if __name__ == "__main__":
    test_tecdoc_fallback()
