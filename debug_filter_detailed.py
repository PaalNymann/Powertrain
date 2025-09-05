#!/usr/bin/env python3
"""
Detailed debug to find why filter works in debug but not in sync_service
"""

import os
import sys
import requests
from dotenv import load_dotenv
load_dotenv()

# Import filter functions from sync_service
sys.path.append('/Users/nyman/powertrain_system')
from sync_service import filter_keep, extract_custom_field, get_i_nettbutikk_from_metadata, fetch_all_rackbeat

# ---------- ENV ----------
RACKBEAT_API = os.getenv("RACKBEAT_ENDPOINT", "https://app.rackbeat.com/api/products")
RACKBEAT_KEY = os.getenv("RACKBEAT_API_KEY")

HEAD_RACK = {
    "Authorization": f"Bearer {RACKBEAT_KEY}",
    "Content-Type": "application/json"
}

def test_full_fetch_vs_sample():
    """Compare filter results between full fetch (like sync) vs sample fetch (like debug)"""
    print("🔍 COMPARING FULL FETCH VS SAMPLE FETCH")
    print("=" * 60)
    
    # Method 1: Sample fetch (like debug script)
    print("📥 METHOD 1: Sample fetch (first 50 products)...")
    params = {
        "limit": 50,
        "page": 1,
        "fields": "number,name,sales_price,available_quantity,group,metadata"
    }
    
    try:
        r = requests.get(RACKBEAT_API, headers=HEAD_RACK, params=params, timeout=30)
        r.raise_for_status()
        js = r.json()
        sample_products = js.get("products", [])
        
        sample_kept = [p for p in sample_products if filter_keep(p)]
        sample_total = len(sample_products)
        sample_kept_count = len(sample_kept)
        
        print(f"   📊 Sample: {sample_kept_count}/{sample_total} products kept")
        print(f"   📊 Sample rate: {sample_kept_count/sample_total*100:.1f}%")
        
    except Exception as e:
        print(f"❌ Error in sample fetch: {e}")
        return
    
    # Method 2: Full fetch (like sync_service)
    print("\\n📥 METHOD 2: Full fetch (all pages like sync)...")
    
    try:
        print("   🔄 Fetching all Rackbeat products...")
        all_products = fetch_all_rackbeat()
        
        print(f"   📊 Total products fetched: {len(all_products)}")
        
        # Apply filter to all products
        print("   🔄 Applying filter to all products...")
        full_kept = []
        full_filtered = []
        
        for p in all_products:
            if filter_keep(p):
                full_kept.append(p)
            else:
                full_filtered.append(p)
        
        full_kept_count = len(full_kept)
        full_total = len(all_products)
        
        print(f"   📊 Full: {full_kept_count}/{full_total} products kept")
        print(f"   📊 Full rate: {full_kept_count/full_total*100:.1f}%")
        
    except Exception as e:
        print(f"❌ Error in full fetch: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Compare results
    print("\\n" + "=" * 60)
    print("📊 COMPARISON RESULTS:")
    print("=" * 60)
    
    print(f"Sample method: {sample_kept_count}/{sample_total} kept ({sample_kept_count/sample_total*100:.1f}%)")
    print(f"Full method:   {full_kept_count}/{full_total} kept ({full_kept_count/full_total*100:.1f}%)")
    
    if full_kept_count > 1000:
        print("\\n⚠️  CRITICAL: Full fetch keeps too many products!")
        print("   This explains why sync shows 3483 products.")
        
        # Analyze why so many are kept
        print("\\n🔍 ANALYZING WHY SO MANY PRODUCTS ARE KEPT:")
        
        # Group analysis
        group_counts = {}
        i_nettbutikk_counts = {}
        
        for p in full_kept[:100]:  # Analyze first 100 kept products
            group_name = p.get("group", {}).get("name", "UNKNOWN")
            i_nb = extract_custom_field(p, "i_nettbutikk").lower()
            
            group_counts[group_name] = group_counts.get(group_name, 0) + 1
            i_nettbutikk_counts[i_nb] = i_nettbutikk_counts.get(i_nb, 0) + 1
        
        print("   📊 Groups in kept products:")
        for group, count in sorted(group_counts.items()):
            print(f"      {group}: {count}")
        
        print("   📊 i_nettbutikk values in kept products:")
        for value, count in sorted(i_nettbutikk_counts.items()):
            print(f"      '{value}': {count}")
        
        # Check if filter is actually being applied
        print("\\n🔍 CHECKING FILTER APPLICATION:")
        
        # Test filter on some products that should be filtered out
        other_group_products = [p for p in all_products if p.get("group", {}).get("name", "") not in ["Drivaksel", "Mellomaksel"]]
        
        if other_group_products:
            print(f"   📊 Found {len(other_group_products)} products in other groups")
            
            # Test filter on first few
            for i, p in enumerate(other_group_products[:5], 1):
                group_name = p.get("group", {}).get("name", "UNKNOWN")
                should_keep = filter_keep(p)
                print(f"   {i}. Group: {group_name}, Filter result: {'KEEP' if should_keep else 'FILTER'}")
                
                if should_keep:
                    print(f"      ⚠️  BUG: Product in group '{group_name}' was kept!")
    
    else:
        print("\\n✅ Full fetch results look reasonable.")
    
    # Show some examples of kept products
    if full_kept:
        print("\\n✅ EXAMPLES OF KEPT PRODUCTS:")
        for i, p in enumerate(full_kept[:10], 1):
            number = p.get("number", "N/A")
            group = p.get("group", {}).get("name", "N/A")
            i_nb = extract_custom_field(p, "i_nettbutikk")
            print(f"   {i}. {number} (Group: {group}, i_nb: '{i_nb}')")

if __name__ == "__main__":
    test_full_fetch_vs_sample()
