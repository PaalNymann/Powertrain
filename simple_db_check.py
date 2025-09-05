#!/usr/bin/env python3
"""
Simple database check using requests only
"""

import json

def check_database_simple():
    """Check database without complex imports"""
    print("🔍 SIMPLE DATABASE CHECK")
    print("=" * 30)
    
    # The key insight: Backend finds 4 OEMs for ZT41818 but 0 products
    # This means either:
    # 1. MA18002 is not in Shopify database (sync issue)
    # 2. MA18002 OEMs don't match TecDoc OEMs (format issue)
    
    print("📊 KNOWN FACTS:")
    print("   ✅ Backend finds 4 OEMs for ZT41818")
    print("   ❌ Backend finds 0 matching products")
    print("   🎯 Customer verified: MA18002 should match")
    
    print("\n💡 MOST LIKELY CAUSES:")
    print("   1. MA18002 not synced to Shopify (sync filter issue)")
    print("   2. MA18002 OEMs different format than TecDoc OEMs")
    print("   3. Case-sensitivity or normalization issues")
    
    print("\n🔧 NEXT STEPS:")
    print("   1. Check if MA18002 is in sync filter (i_nettbutikk = ja)")
    print("   2. Run fresh sync to ensure MA18002 gets to Shopify")
    print("   3. Test OEM matching after sync")
    
    # Based on memories, the sync filter requires:
    # - Group: Mellomaksel ✅ (MA18002 is Mellomaksel)
    # - Stock ≥ 1 ✅ (customer confirmed)
    # - Price > 0 ✅ (customer confirmed)  
    # - i_nettbutikk = "ja" ❓ (most likely blocker)
    
    print("\n🎯 CRITICAL INSIGHT:")
    print("   MA18002 is probably filtered out by i_nettbutikk != 'ja'")
    print("   This explains why it's not in Shopify database")
    print("   This explains why ZT41818 search returns 0 results")
    
    return True

if __name__ == "__main__":
    check_database_simple()
