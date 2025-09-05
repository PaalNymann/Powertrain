#!/usr/bin/env python3
"""
Debug script that uses EXACT same code as sync_service.py to find the bug
"""

import os
import sys
from dotenv import load_dotenv
load_dotenv()

# Import EXACT same functions from sync_service
sys.path.append('/Users/nyman/powertrain_system')
from sync_service import fetch_all_rackbeat, filter_keep

def debug_exact_sync_logic():
    """Use EXACT same logic as sync_service.py to debug filter"""
    print("🔍 DEBUGGING EXACT SYNC LOGIC")
    print("=" * 50)
    
    try:
        print("📥 Step 1: Fetching ALL Rackbeat products (same as sync)...")
        rack_all = fetch_all_rackbeat()
        print(f"✅ Total products fetched: {len(rack_all)}")
        
        print("\\n🔍 Step 2: Applying filter_keep to ALL products (same as sync)...")
        filtered = []
        
        for i, p in enumerate(rack_all):
            if i % 1000 == 0:
                print(f"   Processing {i}/{len(rack_all)}...")
            
            if filter_keep(p):
                filtered.append(p)
        
        print(f"\\n📊 EXACT SYNC RESULTS:")
        print(f"   Total products: {len(rack_all)}")
        print(f"   Filtered products: {len(filtered)}")
        print(f"   Filter rate: {len(filtered)/len(rack_all)*100:.1f}%")
        
        if len(filtered) != 296:
            print(f"\\n❌ MISMATCH FOUND!")
            print(f"   Expected: ~296 products")
            print(f"   Actual: {len(filtered)} products")
            print(f"   This explains why sync shows wrong count!")
            
            # Analyze first 20 kept products
            print(f"\\n🔍 ANALYZING KEPT PRODUCTS:")
            for i, p in enumerate(filtered[:20], 1):
                number = p.get("number", "N/A")
                group = p.get("group", {}).get("name", "N/A")
                from sync_service import extract_custom_field
                i_nb = extract_custom_field(p, "i_nettbutikk")
                print(f"   {i:2d}. {number:15s} | {group:12s} | i_nb: '{i_nb}'")
            
            if len(filtered) > 20:
                print(f"   ... and {len(filtered) - 20} more")
            
            # Check for wrong groups
            group_counts = {}
            for p in filtered:
                group = p.get("group", {}).get("name", "UNKNOWN")
                group_counts[group] = group_counts.get(group, 0) + 1
            
            print(f"\\n📊 GROUP DISTRIBUTION IN FILTERED PRODUCTS:")
            for group, count in sorted(group_counts.items()):
                status = "✅" if group in ["Drivaksel", "Mellomaksel"] else "❌ WRONG"
                print(f"   {status} {group}: {count} products")
            
            # Check i_nettbutikk values
            i_nb_counts = {}
            for p in filtered:
                from sync_service import extract_custom_field
                i_nb = extract_custom_field(p, "i_nettbutikk")
                i_nb_counts[i_nb] = i_nb_counts.get(i_nb, 0) + 1
            
            print(f"\\n📊 I_NETTBUTIKK DISTRIBUTION IN FILTERED PRODUCTS:")
            for value, count in sorted(i_nb_counts.items()):
                status = "✅" if value == "ja" else "❌ WRONG"
                print(f"   {status} '{value}': {count} products")
        
        else:
            print(f"\\n✅ Filter count matches expected!")
        
        # Test specific products
        print(f"\\n🎯 TESTING SPECIFIC PRODUCTS IN FILTERED LIST:")
        test_products = ["MA18002", "MA18001PT", "18-353040"]
        
        for product_number in test_products:
            found = False
            for p in filtered:
                if p.get("number") == product_number:
                    found = True
                    group = p.get("group", {}).get("name", "N/A")
                    from sync_service import extract_custom_field
                    i_nb = extract_custom_field(p, "i_nettbutikk")
                    print(f"   ✅ {product_number}: Found (Group: {group}, i_nb: '{i_nb}')")
                    break
            
            if not found:
                print(f"   ❌ {product_number}: NOT in filtered list")
        
        return len(filtered)
        
    except Exception as e:
        print(f"❌ Error in exact sync debug: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    print("🚀 STARTING EXACT SYNC DEBUG")
    print("=" * 60)
    
    filtered_count = debug_exact_sync_logic()
    
    print(f"\\n🎉 EXACT SYNC DEBUG COMPLETED")
    print("=" * 60)
    
    if filtered_count is not None:
        if filtered_count > 1000:
            print("⚠️  CRITICAL: Filter is broken - too many products!")
            print("   This explains why sync shows 3483 products.")
        elif filtered_count < 100:
            print("⚠️  Filter is too restrictive.")
        else:
            print("✅ Filter count looks reasonable.")
        
        print(f"\\n🎯 CONCLUSION:")
        print(f"   Exact sync logic would sync: {filtered_count} products")
        print(f"   This should match what sync_service.py shows")
    else:
        print("❌ Debug failed - could not determine filter count")
