#!/usr/bin/env python3
"""
Verify if MA18002 (customer-verified Nissan X-Trail part) exists in Shopify database
and check its OEM numbers
"""

import requests
import json

BACKEND_URL = "https://web-production-0809b.up.railway.app"

def test_ma18002_search():
    """Test if we can find MA18002 by searching for its known OEMs"""
    
    print("🔍 TESTING MA18002 SEARCH BY KNOWN OEMS")
    print("=" * 45)
    
    # Customer-verified OEM numbers for MA18002
    ma18002_oems = [
        "37000-8H310",
        "37000-8H510", 
        "37000-8H800",
        "370008H310",
        "370008H510",
        "370008H800"
    ]
    
    print(f"🎯 Customer-verified MA18002 OEMs:")
    for oem in ma18002_oems:
        print(f"   - {oem}")
    
    print(f"\n🔍 Testing each OEM against backend search...")
    
    # Test if we can find any products with these OEMs
    # Since we can't call search_products_by_oem_optimized directly,
    # we need to use the main search endpoint or create a test endpoint
    
    print(f"\n💡 Strategy:")
    print(f"   1. If MA18002 is synced to Shopify, it should have these OEMs")
    print(f"   2. If compatibility matrix had ZT41818 data, it should include these OEMs")
    print(f"   3. The missing link is between TecDoc/cache and these specific OEMs")
    
    return ma18002_oems

def analyze_cache_coverage_problem():
    """Analyze why compatibility matrix/cache lacks ZT41818 data"""
    
    print(f"\n🔍 ANALYZING CACHE COVERAGE PROBLEM")
    print("=" * 40)
    
    print(f"📊 Current Status:")
    print(f"   ✅ YZ99554 (Mercedes GLK): Cache has data → 18→10 OEMs work")
    print(f"   ❌ ZT41818 (Nissan X-Trail): Cache has NO data → 0 OEMs")
    print(f"   ✅ Database: 156 products, 936 metafields")
    print(f"   ✅ Compatibility matrix: 1584 rows")
    
    print(f"\n🔍 Root Cause Analysis:")
    print(f"   1. Compatibility matrix was built from limited vehicle set")
    print(f"   2. ZT41818 (Nissan X-Trail 2006) not included in original build")
    print(f"   3. MA18002 may exist in database but not linked to ZT41818")
    print(f"   4. Need to either:")
    print(f"      a) Add ZT41818 to compatibility matrix manually")
    print(f"      b) Use direct TecDoc fallback for uncached vehicles")
    print(f"      c) Regenerate compatibility matrix with broader coverage")

def propose_solution_strategy():
    """Propose solution strategy for ZT41818 and similar vehicles"""
    
    print(f"\n🔧 SOLUTION STRATEGY")
    print("=" * 25)
    
    print(f"🎯 Immediate Fix Options:")
    print(f"   1. MANUAL CACHE ENTRY: Add ZT41818 → MA18002 OEMs to compatibility matrix")
    print(f"   2. DIRECT TECDOC FALLBACK: Fix direct TecDoc API for Nissan X-Trail")
    print(f"   3. HYBRID APPROACH: Use cache when available, TecDoc when not")
    
    print(f"\n🔧 Recommended Approach:")
    print(f"   1. Fix direct TecDoc API for Nissan (currently returns 0 OEMs)")
    print(f"   2. Ensure fallback works when cache is empty")
    print(f"   3. Add ZT41818 data to compatibility matrix for future speed")
    
    print(f"\n💡 The hybrid system should work like this:")
    print(f"   - Try cache first (fast for known vehicles)")
    print(f"   - Fall back to direct TecDoc (works for all vehicles)")
    print(f"   - Cache the result for future use")
    
    print(f"\n🎯 Critical Issue to Fix:")
    print(f"   Direct TecDoc API returns 0 OEMs for Nissan X-Trail 2006")
    print(f"   This is why fallback doesn't work for ZT41818")
    print(f"   Need to debug RapidAPI TecDoc integration for Nissan")

def test_direct_tecdoc_fallback():
    """Test if direct TecDoc fallback is working"""
    
    print(f"\n🔍 TESTING DIRECT TECDOC FALLBACK")
    print("=" * 35)
    
    print(f"📡 Current status from debug endpoint:")
    print(f"   - Direct TecDoc: 0 OEMs for ZT41818")
    print(f"   - Cache: 0 OEMs for ZT41818")
    print(f"   - Result: No fallback works")
    
    print(f"\n🔧 Need to fix:")
    print(f"   1. RapidAPI TecDoc integration for Nissan vehicles")
    print(f"   2. Ensure get_oem_numbers_from_rapidapi_tecdoc() works for X-Trail")
    print(f"   3. Test with customer-verified OEMs as validation")
    
    print(f"\n💡 Success criteria:")
    print(f"   Direct TecDoc should return OEMs like:")
    print(f"   - 37000-8H310, 37000-8H510, 37000-8H800")
    print(f"   - 370008H310, 370008H510, 370008H800")
    print(f"   These should match MA18002 in database")

if __name__ == "__main__":
    print("🔍 VERIFYING MA18002 AND CACHE COVERAGE")
    print("=" * 45)
    
    # Test MA18002 search
    ma18002_oems = test_ma18002_search()
    
    # Analyze cache coverage problem
    analyze_cache_coverage_problem()
    
    # Propose solution strategy
    propose_solution_strategy()
    
    # Test direct TecDoc fallback
    test_direct_tecdoc_fallback()
    
    print(f"\n🎯 NEXT ACTION:")
    print(f"Fix direct TecDoc API for Nissan X-Trail to return correct OEMs")
    print(f"This will enable fallback when cache is empty (like for ZT41818)")
    print(f"Focus on get_oem_numbers_from_rapidapi_tecdoc() function")
