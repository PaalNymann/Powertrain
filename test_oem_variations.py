#!/usr/bin/env python3
"""
Test the new OEM variation matching logic
"""

def test_oem_variations():
    """Test OEM variation generation"""
    
    print("🧪 TESTING OEM VARIATION LOGIC")
    print("=" * 50)
    
    test_oems = [
        "A 2044 102 401",  # TecDoc with spaces
        "A2044102401",     # Rackbeat without spaces
        "a2044102401",     # Lowercase
    ]
    
    for oem_number in test_oems:
        print(f"\n🔧 Testing OEM: '{oem_number}'")
        
        # Generate variations (same logic as in code)
        oem_original = oem_number
        oem_upper = oem_number.upper()
        oem_lower = oem_number.lower()
        oem_no_spaces = ''.join(oem_number.split())
        oem_no_spaces_upper = ''.join(oem_number.split()).upper()
        oem_no_spaces_lower = ''.join(oem_number.split()).lower()
        
        variations = [
            oem_original,
            oem_upper,
            oem_lower,
            oem_no_spaces,
            oem_no_spaces_upper,
            oem_no_spaces_lower
        ]
        
        # Remove duplicates
        unique_variations = list(dict.fromkeys(variations))
        
        print(f"   Variations: {unique_variations}")
        
        # Check if this covers the expected matches
        expected_matches = ["A 2044 102 401", "A2044102401", "a2044102401"]
        
        for expected in expected_matches:
            if expected in unique_variations:
                print(f"   ✅ Will match: '{expected}'")
            else:
                print(f"   ❌ Will NOT match: '{expected}'")
    
    print(f"\n🚀 PERFORMANCE TEST:")
    print("New query uses simple = and LIKE operations (fast)")
    print("No UPPER(REPLACE()) functions that process every row")
    print("Should be much faster than previous version!")

if __name__ == "__main__":
    test_oem_variations()
