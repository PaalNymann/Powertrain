#!/usr/bin/env python3
"""
Simple debug script to test MA18002 metadata extraction logic
No external dependencies required
"""

import json

def extract_custom_field(product, field_name):
    """Extract custom field from product metadata - copied from sync_service.py"""
    metadata = product.get('metadata', [])
    
    # Try different slug formats
    possible_slugs = [
        field_name,
        field_name.replace('_', '-'),
        field_name.replace('-', '_'),
        field_name.lower(),
        field_name.upper()
    ]
    
    for item in metadata:
        if item.get('slug') in possible_slugs:
            return item.get('value', '')
    
    return ''

def get_i_nettbutikk_from_metadata(metadata):
    """Extract i_nettbutikk field from metadata - copied from sync_service.py"""
    for item in metadata:
        slug = item.get('slug', '').lower()
        if slug in ['i-nettbutikk', 'i_nettbutikk', 'nettbutikk']:
            value = item.get('value', '').lower().strip()
            return value
    return ''

def debug_metadata_fields(product):
    """Debug all metadata fields"""
    metadata = product.get('metadata', [])
    print(f'   Total metadata items: {len(metadata)}')
    for i, item in enumerate(metadata):
        slug = item.get('slug', 'NO_SLUG')
        value = item.get('value', 'NO_VALUE')
        print(f'   [{i}] slug: "{slug}" -> value: "{value}"')

def filter_keep(product):
    """Filter logic - copied from sync_service.py"""
    
    # Check group
    group_name = product.get('group', {}).get('name', '')
    if group_name not in ['Drivaksel', 'Mellomaksel']:
        print(f'   ❌ GROUP FILTER: "{group_name}" not in [Drivaksel, Mellomaksel]')
        return False
    
    # Check stock
    available_quantity = product.get('available_quantity', 0)
    if available_quantity < 1:
        print(f'   ❌ STOCK FILTER: {available_quantity} < 1')
        return False
    
    # Check price
    sales_price = product.get('sales_price', 0)
    if sales_price <= 0:
        print(f'   ❌ PRICE FILTER: {sales_price} <= 0')
        return False
    
    # Check i_nettbutikk
    i_nettbutikk = get_i_nettbutikk_from_metadata(product.get('metadata', []))
    if i_nettbutikk != 'ja':
        print(f'   ❌ i_nettbutikk FILTER: "{i_nettbutikk}" != "ja"')
        return False
    
    print(f'   ✅ ALL FILTERS PASSED')
    return True

def test_ma18002_scenarios():
    """Test different MA18002 scenarios"""
    
    print('🔍 TESTING MA18002 METADATA EXTRACTION SCENARIOS')
    print('=' * 70)
    
    # Scenario 1: Standard format (what we expect)
    scenario1 = {
        "number": "MA18002",
        "name": "Nissan X-Trail Lz2035/30",
        "group": {"name": "Mellomaksel"},
        "available_quantity": 5,
        "sales_price": 1500.0,
        "metadata": [
            {"slug": "i-nettbutikk", "value": "ja"},
            {"slug": "original-nummer", "value": "37000-8H310, 37000-8H510"}
        ]
    }
    
    # Scenario 2: Underscore format
    scenario2 = {
        "number": "MA18002", 
        "name": "Nissan X-Trail Lz2035/30",
        "group": {"name": "Mellomaksel"},
        "available_quantity": 5,
        "sales_price": 1500.0,
        "metadata": [
            {"slug": "i_nettbutikk", "value": "ja"},
            {"slug": "original_nummer", "value": "37000-8H310, 37000-8H510"}
        ]
    }
    
    # Scenario 3: Case variations
    scenario3 = {
        "number": "MA18002",
        "name": "Nissan X-Trail Lz2035/30", 
        "group": {"name": "Mellomaksel"},
        "available_quantity": 5,
        "sales_price": 1500.0,
        "metadata": [
            {"slug": "I-NETTBUTIKK", "value": "JA"},
            {"slug": "ORIGINAL-NUMMER", "value": "37000-8H310, 37000-8H510"}
        ]
    }
    
    # Scenario 4: Wrong value
    scenario4 = {
        "number": "MA18002",
        "name": "Nissan X-Trail Lz2035/30",
        "group": {"name": "Mellomaksel"},
        "available_quantity": 5,
        "sales_price": 1500.0,
        "metadata": [
            {"slug": "i-nettbutikk", "value": "nei"},  # Wrong value!
            {"slug": "original-nummer", "value": "37000-8H310, 37000-8H510"}
        ]
    }
    
    # Scenario 5: Missing i_nettbutikk
    scenario5 = {
        "number": "MA18002",
        "name": "Nissan X-Trail Lz2035/30",
        "group": {"name": "Mellomaksel"},
        "available_quantity": 5,
        "sales_price": 1500.0,
        "metadata": [
            {"slug": "original-nummer", "value": "37000-8H310, 37000-8H510"}
            # No i_nettbutikk field!
        ]
    }
    
    scenarios = [
        ("Standard format (i-nettbutikk: ja)", scenario1),
        ("Underscore format (i_nettbutikk: ja)", scenario2),
        ("Case variations (I-NETTBUTIKK: JA)", scenario3),
        ("Wrong value (i-nettbutikk: nei)", scenario4),
        ("Missing i_nettbutikk field", scenario5)
    ]
    
    for name, scenario in scenarios:
        print(f'\n📋 SCENARIO: {name}')
        print(f'   Product: {scenario["number"]} - {scenario["name"]}')
        
        # Debug metadata
        debug_metadata_fields(scenario)
        
        # Test extraction
        i_nettbutikk = get_i_nettbutikk_from_metadata(scenario.get('metadata', []))
        print(f'   Extracted i_nettbutikk: "{i_nettbutikk}"')
        
        # Test filter
        should_sync = filter_keep(scenario)
        print(f'   RESULT: {"✅ WOULD SYNC" if should_sync else "❌ FILTERED OUT"}')

def test_slug_variations():
    """Test different possible slug formats"""
    
    print(f'\n🔍 TESTING DIFFERENT SLUG FORMATS')
    print('=' * 50)
    
    base_product = {
        "number": "MA18002",
        "name": "Test Product",
        "group": {"name": "Mellomaksel"},
        "available_quantity": 1,
        "sales_price": 100.0
    }
    
    slug_tests = [
        "i-nettbutikk",
        "i_nettbutikk", 
        "I-NETTBUTIKK",
        "I_NETTBUTIKK",
        "nettbutikk",
        "NETTBUTIKK",
        "webshop",
        "online"
    ]
    
    for slug in slug_tests:
        test_product = base_product.copy()
        test_product["metadata"] = [{"slug": slug, "value": "ja"}]
        
        extracted = get_i_nettbutikk_from_metadata(test_product.get('metadata', []))
        result = "✅ FOUND" if extracted == "ja" else "❌ NOT FOUND"
        print(f'   Slug "{slug}": "{extracted}" -> {result}')

if __name__ == '__main__':
    test_ma18002_scenarios()
    test_slug_variations()
    
    print(f'\n🎯 DEBUGGING SUMMARY:')
    print(f'If MA18002 is not syncing, check:')
    print(f'1. Metadata slug format (i-nettbutikk vs i_nettbutikk)')
    print(f'2. Value is exactly "ja" (not "JA", "Ja", " ja ", etc.)')
    print(f'3. Field exists in Rackbeat metadata')
    print(f'4. Group is exactly "Mellomaksel" (not "mellomaksel")')
    print(f'5. Stock > 0 and price > 0')
