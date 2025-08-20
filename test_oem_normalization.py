#!/usr/bin/env python3
"""
Test OEM normalization logic locally before deployment
"""

def test_oem_normalization():
    """Test the OEM normalization logic"""
    
    print("🧪 TESTING OEM NORMALIZATION LOGIC")
    print("=" * 50)
    
    # Test cases
    test_cases = [
        ("A 2044 102 401", "A2044102401"),  # TecDoc with spaces
        ("a 2044 102 401", "A2044102401"),  # Lowercase with spaces
        ("A2044102401", "A2044102401"),     # Already normalized
        ("2044102401", "2044102401"),       # Without prefix
        ("A 2044-102-401", "A2044-102-401"), # With dashes
        ("", ""),                           # Empty string
    ]
    
    print("🔧 Testing normalization function:")
    for original, expected in test_cases:
        # Normalize: remove spaces and convert to uppercase
        normalized = ''.join(original.split()).upper()
        
        status = "✅" if normalized == expected else "❌"
        print(f"   {status} '{original}' → '{normalized}' (expected: '{expected}')")
        
        if normalized != expected:
            print(f"      ⚠️  MISMATCH!")
    
    print(f"\n🔍 SQL Query Performance Test:")
    print("Original query (fast):")
    print("   WHERE pm.value = 'A2044102401'")
    
    print("New query (potentially slow):")
    print("   WHERE UPPER(REPLACE(pm.value, ' ', '')) = 'A2044102401'")
    
    print(f"\n💡 POTENTIAL ISSUE:")
    print("The new SQL query applies UPPER(REPLACE()) to EVERY row in the database")
    print("This could cause significant performance degradation and timeouts!")
    
    print(f"\n🚀 BETTER SOLUTION:")
    print("1. Normalize OEM numbers BEFORE storing in database")
    print("2. OR create a computed column/index for normalized OEMs")
    print("3. OR normalize the search term and use a simpler query")

if __name__ == "__main__":
    test_oem_normalization()
