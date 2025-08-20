#!/usr/bin/env python3
"""
Test the complete license plate → OEM → product matching flow
"""

def simulate_oem_matching(cache_oems, database_oems):
    """Simulate the new OEM variation matching logic"""
    
    matches = []
    
    for cache_oem in cache_oems:
        print(f"🔍 Testing cache OEM: '{cache_oem}'")
        
        # Generate variations (same logic as in optimized_search.py)
        oem_original = cache_oem
        oem_upper = cache_oem.upper()
        oem_lower = cache_oem.lower()
        oem_no_spaces = ''.join(cache_oem.split())
        oem_no_spaces_upper = ''.join(cache_oem.split()).upper()
        oem_no_spaces_lower = ''.join(cache_oem.split()).lower()
        
        variations = [
            oem_original,
            oem_upper,
            oem_lower,
            oem_no_spaces,
            oem_no_spaces_upper,
            oem_no_spaces_lower
        ]
        
        # Check if any variation matches database OEMs
        for db_oem in database_oems:
            if db_oem in variations:
                matches.append((cache_oem, db_oem))
                print(f"   ✅ MATCH: '{cache_oem}' → '{db_oem}'")
                break
        else:
            print(f"   ❌ NO MATCH for '{cache_oem}'")
    
    return matches

def test_license_plates():
    """Test the complete flow for our problem license plates"""
    
    print("🧪 TESTING LICENSE PLATE → OEM → PRODUCT MATCHING")
    print("=" * 60)
    
    # Test scenarios based on what we know
    test_scenarios = [
        {
            "license_plate": "YZ99554",
            "vehicle": "MERCEDES-BENZ GLK 2010",
            "cache_oems": ["A 2044 102 401", "A 2044 106 901", "2044 102 401"],  # TecDoc format with spaces
            "database_oems": ["A2044102401", "A2044106901", "2044102401", "VITO123", "SPRINTER456"],  # Rackbeat format without spaces
            "expected_matches": 3,
            "should_exclude": ["VITO123", "SPRINTER456"]
        },
        {
            "license_plate": "KH66644", 
            "vehicle": "VOLKSWAGEN TIGUAN 2009",
            "cache_oems": ["1K0 407 271 AK", "1K0407271AK", "1K0 407 272"],  # Potential VW OEMs
            "database_oems": ["1K0407271AK", "1K0407272", "TOYOTA123"],  # Database format
            "expected_matches": 2,
            "should_exclude": ["TOYOTA123"]
        },
        {
            "license_plate": "RJ62438",
            "vehicle": "VOLVO V70 2006", 
            "cache_oems": ["30735120", "30 735 120", "8251497"],  # Potential Volvo OEMs
            "database_oems": ["30735120", "8251497", "HONDA123"],  # Database format
            "expected_matches": 2,
            "should_exclude": ["HONDA123"]
        }
    ]
    
    for scenario in test_scenarios:
        print(f"\n🚗 Testing {scenario['license_plate']}: {scenario['vehicle']}")
        print("-" * 50)
        
        print(f"📋 Cache OEMs (TecDoc): {scenario['cache_oems']}")
        print(f"📋 Database OEMs (Rackbeat): {scenario['database_oems']}")
        
        # Simulate OEM matching
        matches = simulate_oem_matching(scenario['cache_oems'], scenario['database_oems'])
        
        print(f"\n📊 Results:")
        print(f"   Found {len(matches)} matches (expected: {scenario['expected_matches']})")
        
        for cache_oem, db_oem in matches:
            if db_oem in scenario['should_exclude']:
                print(f"   ⚠️  PROBLEM: '{db_oem}' should be excluded!")
            else:
                print(f"   ✅ Valid match: '{cache_oem}' → '{db_oem}'")
        
        # Check if we found expected number of matches
        if len(matches) >= scenario['expected_matches']:
            print(f"   🎯 SUCCESS: Found sufficient matches")
        else:
            print(f"   ❌ PROBLEM: Too few matches found")
    
    print(f"\n🚀 CONCLUSION:")
    print("If this test shows good results, the new OEM variation logic should work!")
    print("Key improvements:")
    print("✅ Handles spaces: 'A 2044 102 401' → 'A2044102401'")
    print("✅ Handles case: 'a2044102401' → 'A2044102401'") 
    print("✅ Fast performance: No UPPER(REPLACE()) on every row")
    print("✅ PostgreSQL compatible: Standard SQL syntax")

if __name__ == "__main__":
    test_license_plates()
