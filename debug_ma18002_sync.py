#!/usr/bin/env python3
"""
Debug script to check why MA18002 is not being synced
Focus on i_nettbutikk field extraction from Rackbeat metadata
"""

import os
import sys
import json

# Add current directory to path to import sync functions
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import sync functions for testing
from sync_service import extract_custom_field, get_i_nettbutikk_from_metadata, debug_metadata_fields, filter_keep

def simulate_ma18002_product():
    """Simulate MA18002 product structure based on expected Rackbeat format"""
    
    # This is what we expect MA18002 to look like in Rackbeat
    ma18002_product = {
        "number": "MA18002",
        "name": "Nissan X-Trail Lz2035/30",
        "group": {"name": "Mellomaksel"},
        "available_quantity": 5,  # Should be > 0
        "sales_price": 1500.0,   # Should be > 0
        "metadata": [
            {
                "slug": "i-nettbutikk",  # Most likely format
                "value": "ja"
            },
            {
                "slug": "original-nummer",
                "value": "37000-8H310, 37000-8H510, 37000-8H800, 370008H310, 370008H510, 370008H800"
            }
        ]
    }
    
    return ma18002_product

def test_extraction_logic():
    """Test the extraction logic with simulated MA18002 data"""
    
    print('🔍 TESTING MA18002 METADATA EXTRACTION...')
    print('=' * 60)
    
    # Get simulated product
    product = simulate_ma18002_product()
    
    print(f'📦 PRODUCT: {product["name"]}')
    print(f'   Number: {product["number"]}')
    print(f'   Group: {product["group"]["name"]}')
    print(f'   Stock: {product["available_quantity"]}')
    print(f'   Price: {product["sales_price"]}')
    
    # Debug all metadata fields
    print(f'\n🔍 ALL METADATA FIELDS:')
    debug_metadata_fields(product)
    
    # Test i_nettbutikk extraction
    print(f'\n🔍 TESTING i_nettbutikk EXTRACTION:')
    
    # Test direct metadata function
    i_nettbutikk_direct = get_i_nettbutikk_from_metadata(product.get('metadata', []))
    print(f'   get_i_nettbutikk_from_metadata(): "{i_nettbutikk_direct}"')
    
    # Test via extract_custom_field
    i_nettbutikk_custom = extract_custom_field(product, "i_nettbutikk")
    print(f'   extract_custom_field(): "{i_nettbutikk_custom}"')
    
    # Test filter_keep function
    print(f'\n🔍 TESTING filter_keep() FUNCTION:')
    should_keep = filter_keep(product)
    print(f'   filter_keep() result: {should_keep}')
    
    if should_keep:
        print(f'   ✅ MA18002 WOULD BE SYNCED!')
    else:
        print(f'   ❌ MA18002 WOULD BE FILTERED OUT!')
    
    # Test different slug variations
    print(f'\n🔍 TESTING DIFFERENT SLUG VARIATIONS:')
    
    slug_variations = [
        "i-nettbutikk",
        "i_nettbutikk", 
        "nettbutikk",
        "webshop",
        "online"
    ]
    
    for slug in slug_variations:
        test_product = product.copy()
        test_product["metadata"] = [
            {
                "slug": slug,
                "value": "ja"
            }
        ]
        
        extracted = get_i_nettbutikk_from_metadata(test_product.get('metadata', []))
        print(f'   Slug "{slug}": "{extracted}" -> {"✅ FOUND" if extracted == "ja" else "❌ NOT FOUND"}')

def test_real_rackbeat_format():
    """Test with different possible Rackbeat metadata formats"""
    
    print(f'\n🔍 TESTING DIFFERENT RACKBEAT FORMATS:')
    print('=' * 60)
    
    # Format 1: Standard slug format
    format1 = {
        "number": "MA18002",
        "name": "Test Product",
        "group": {"name": "Mellomaksel"},
        "available_quantity": 1,
        "sales_price": 100.0,
        "metadata": [
            {"slug": "i-nettbutikk", "value": "ja"}
        ]
    }
    
    # Format 2: Underscore format
    format2 = {
        "number": "MA18002",
        "name": "Test Product", 
        "group": {"name": "Mellomaksel"},
        "available_quantity": 1,
        "sales_price": 100.0,
        "metadata": [
            {"slug": "i_nettbutikk", "value": "ja"}
        ]
    }
    
    # Format 3: Different case
    format3 = {
        "number": "MA18002",
        "name": "Test Product",
        "group": {"name": "Mellomaksel"}, 
        "available_quantity": 1,
        "sales_price": 100.0,
        "metadata": [
            {"slug": "I-NETTBUTIKK", "value": "JA"}
        ]
    }
    
    formats = [
        ("Standard (i-nettbutikk)", format1),
        ("Underscore (i_nettbutikk)", format2), 
        ("Uppercase (I-NETTBUTIKK)", format3)
    ]
    
    for name, test_format in formats:
        print(f'\n📋 TESTING {name}:')
        should_keep = filter_keep(test_format)
        print(f'   Result: {"✅ WOULD SYNC" if should_keep else "❌ FILTERED OUT"}')

if __name__ == '__main__':
    test_extraction_logic()
    test_real_rackbeat_format()
    
    print(f'\n🎯 SUMMARY:')
    print(f'If MA18002 is not being synced, the issue is likely:')
    print(f'1. Metadata slug format mismatch (dash vs underscore)')
    print(f'2. Case sensitivity in slug or value')
    print(f'3. Different metadata structure than expected')
    print(f'4. Value is not exactly "ja" (spaces, case, etc.)')
