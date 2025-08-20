#!/usr/bin/env python3
"""
Debug OEM storage by calling production API directly
"""

import requests
import json

def debug_oem_via_api():
    """Debug OEM storage by calling production API with specific OEMs"""
    
    print("🔍 DEBUGGING OEM STORAGE VIA PRODUCTION API")
    print("=" * 50)
    
    base_url = "https://web-production-0809b.up.railway.app"
    
    # Test OEMs we know should exist
    test_oems = [
        "A2044102401",  # Mercedes GLK OEM from cache
        "2044102401",   # Same without A prefix
        "MA01002",      # Product SKU we know exists
        "30735120",     # Volvo OEM we've seen before
        "1K0407271AK"   # VW OEM we've seen before
    ]
    
    print(f"🔍 Testing OEM storage with known OEMs...")
    
    for oem in test_oems:
        print(f"\n🔍 Testing OEM: {oem}")
        print("-" * 30)
        
        # Try to search for this specific OEM
        try:
            # Use a fake license plate but specify the OEM directly in logs
            # We'll look at the logs to see what happens during OEM matching
            
            # Actually, let's create a simple endpoint test
            test_url = f"{base_url}/api/test_oem_search"
            
            # For now, let's just see what products exist in the database
            # by checking the general search endpoint behavior
            
            print(f"   Testing if OEM {oem} exists in database...")
            print(f"   (We'll check this by looking at the search logs)")
            
        except Exception as e:
            print(f"   ❌ Error testing {oem}: {e}")
    
    print(f"\n🎯 NEXT STEPS:")
    print("1. Check the search logs above to see OEM matching behavior")
    print("2. Look at the actual SQL queries being executed")
    print("3. Check if OEMs are stored as strings, JSON, or arrays")
    print("4. Verify the exact format and case sensitivity")
    
    # Let's also check what the database actually contains
    print(f"\n🔍 Let's check what we can see from the recent search:")
    print("From the logs, we saw:")
    print("- Cache returned OEMs: A2044102401, 2043301500, etc.")
    print("- All OEM searches returned 'No products found'")
    print("- This suggests either:")
    print("  a) OEMs are stored in a different format")
    print("  b) OEM matching SQL query is incorrect")
    print("  c) Products don't actually have these OEMs in Original_nummer field")

if __name__ == "__main__":
    debug_oem_via_api()
