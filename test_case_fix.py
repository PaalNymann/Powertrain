#!/usr/bin/env python3
"""
Test the case-sensitivity fix for i_nettbutikk extraction
"""

def get_i_nettbutikk_from_metadata_fixed(metadata):
    """Fixed version with case-insensitive matching"""
    possible_slugs = ['i-nettbutikk', 'i_nettbutikk', 'nettbutikk', 'webshop', 'online']
    for field in metadata:
        slug = field.get('slug', '').lower()  # Convert to lowercase for comparison
        if slug in possible_slugs:
            value = field.get('value', '').lower().strip()  # Also normalize value
            return value
    return ''

def filter_keep_fixed(p):
    """Fixed filter_keep with case-insensitive i_nettbutikk check"""
    # Check stock and price requirements
    if not (p.get("available_quantity",0) >= 1 and p.get("sales_price",0) > 0):
        return False
    
    # Check product group - ONLY Drivaksel and Mellomaksel
    group_name = p.get("group", {}).get("name", "")
    if group_name not in ["Drivaksel", "Mellomaksel"]:
        return False
    
    # Check i_nettbutikk field (webshop availability) - FIXED VERSION
    i_nettbutikk = get_i_nettbutikk_from_metadata_fixed(p.get('metadata', []))
    if i_nettbutikk != "ja":
        print(f"🚫 FILTERED OUT: '{p.get('name', 'N/A')[:30]}' - i_nettbutikk: '{i_nettbutikk}' (Group: {group_name})")
        return False
    
    print(f"✅ KEEPING: '{p.get('name', 'N/A')[:50]}' (Group: {group_name})")
    return True

def test_case_scenarios():
    """Test different case scenarios that would have failed before"""
    
    print("🔍 TESTING CASE-SENSITIVITY FIX")
    print("=" * 50)
    
    # Test cases that would have failed before the fix
    test_cases = [
        {
            "name": "MA18002 - Uppercase slug and value",
            "product": {
                "number": "MA18002",
                "name": "Nissan X-Trail Lz2035/30",
                "group": {"name": "Mellomaksel"},
                "available_quantity": 5,
                "sales_price": 1500.0,
                "metadata": [
                    {"slug": "I-NETTBUTIKK", "value": "JA"},  # Uppercase!
                    {"slug": "ORIGINAL-NUMMER", "value": "37000-8H310"}
                ]
            }
        },
        {
            "name": "Mixed case slug",
            "product": {
                "number": "TEST001",
                "name": "Test Product",
                "group": {"name": "Drivaksel"},
                "available_quantity": 1,
                "sales_price": 100.0,
                "metadata": [
                    {"slug": "i_Nettbutikk", "value": "ja"},  # Mixed case!
                ]
            }
        },
        {
            "name": "Value with spaces",
            "product": {
                "number": "TEST002",
                "name": "Test Product 2",
                "group": {"name": "Mellomaksel"},
                "available_quantity": 1,
                "sales_price": 100.0,
                "metadata": [
                    {"slug": "i-nettbutikk", "value": " JA "},  # Spaces!
                ]
            }
        },
        {
            "name": "Should be filtered out (nei)",
            "product": {
                "number": "TEST003",
                "name": "Test Product 3",
                "group": {"name": "Mellomaksel"},
                "available_quantity": 1,
                "sales_price": 100.0,
                "metadata": [
                    {"slug": "i-nettbutikk", "value": "NEI"},  # Should be filtered
                ]
            }
        }
    ]
    
    for test_case in test_cases:
        print(f"\n📋 TEST: {test_case['name']}")
        product = test_case['product']
        
        # Test extraction
        extracted = get_i_nettbutikk_from_metadata_fixed(product.get('metadata', []))
        print(f"   Extracted i_nettbutikk: '{extracted}'")
        
        # Test filter
        should_sync = filter_keep_fixed(product)
        result = "✅ WOULD SYNC" if should_sync else "❌ FILTERED OUT"
        print(f"   Result: {result}")

if __name__ == '__main__':
    test_case_scenarios()
    
    print(f"\n🎯 SUMMARY:")
    print(f"The case-sensitivity fix should now handle:")
    print(f"- Uppercase slugs: I-NETTBUTIKK, I_NETTBUTIKK")
    print(f"- Mixed case slugs: i_Nettbutikk, I-nettbutikk")
    print(f"- Uppercase values: JA, Ja")
    print(f"- Values with spaces: ' ja ', ' JA '")
    print(f"")
    print(f"🚀 DEPLOY THIS FIX TO RAILWAY TO TEST MA18002!")
