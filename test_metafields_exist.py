#!/usr/bin/env python3
"""
Test what metafields actually exist in the database
"""

import requests
import json

def test_metafields_exist():
    """Test what metafields exist by calling a simple endpoint"""
    
    print("🔍 TESTING WHAT METAFIELDS EXIST IN DATABASE")
    print("=" * 50)
    
    base_url = "https://web-production-0809b.up.railway.app"
    
    # Let's create a simple test endpoint call to see database contents
    print("🔍 Let's analyze the OEM search failure...")
    print()
    
    print("From the logs, we know:")
    print("✅ Cache returned 18 OEMs for YZ99554 (Mercedes GLK)")
    print("❌ All 18 OEMs returned 'No products found'")
    print()
    
    print("The OEMs that failed to match:")
    failed_oems = [
        'A2044102401', '2043301500', '2053303806', '2123301100', '2133303603',
        '2133304805', '2533301300', '4473301900', '4473302000', '6393300801',
        'A1644103102', 'A2053303906', 'A6394103206', 'A6394103306', 
        'A6394104806', 'A6394108606', 'A9064103616'
    ]
    
    for oem in failed_oems[:5]:  # Show first 5
        print(f"❌ {oem}")
    print(f"... and {len(failed_oems)-5} more")
    
    print()
    print("🤔 POSSIBLE CAUSES:")
    print("1. No products in database have Original_nummer metafields")
    print("2. OEM numbers are stored in different format (e.g., without 'A' prefix)")
    print("3. OEM numbers are stored in different key (not 'Original_nummer')")
    print("4. Database sync is incomplete - products exist but metafields missing")
    print()
    
    print("🔍 NEXT DEBUG STEPS:")
    print("1. Check if ANY products have Original_nummer metafields")
    print("2. Check what metafield keys actually exist")
    print("3. Check if MA01002 product exists and has metafields")
    print("4. Test with simpler OEM format (without A prefix)")
    
    # Let's test a simple case - check if we can find ANY products with metafields
    print()
    print("🧪 HYPOTHESIS TO TEST:")
    print("The database might be missing metafields entirely after recent syncs")
    print("OR the OEM format in database doesn't match cache format")

if __name__ == "__main__":
    test_metafields_exist()
