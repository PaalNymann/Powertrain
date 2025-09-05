#!/usr/bin/env python3
"""
Debug filter logic to ensure only Drivaksel and Mellomaksel products with i_nettbutikk: ja are included
"""

import os
import sys
import requests
from dotenv import load_dotenv
load_dotenv()

# Import filter functions from sync_service
sys.path.append('/Users/nyman/powertrain_system')
from sync_service import filter_keep, extract_custom_field, get_i_nettbutikk_from_metadata

# ---------- ENV ----------
RACKBEAT_API = os.getenv("RACKBEAT_ENDPOINT", "https://app.rackbeat.com/api/products")
RACKBEAT_KEY = os.getenv("RACKBEAT_API_KEY")

HEAD_RACK = {
    "Authorization": f"Bearer {RACKBEAT_KEY}",
    "Content-Type": "application/json"
}

def test_filter_logic():
    """Test filter logic on a small sample of products"""
    print("🔍 DEBUGGING FILTER LOGIC")
    print("=" * 50)
    
    # Get first few pages to test filter
    print("📥 Fetching sample products from Rackbeat...")
    
    params = {
        "limit": 50,
        "page": 1,
        "fields": "number,name,sales_price,available_quantity,group,metadata"
    }
    
    try:
        r = requests.get(RACKBEAT_API, headers=HEAD_RACK, params=params, timeout=30)
        r.raise_for_status()
        js = r.json()
        products = js.get("products", [])
        
        print(f"📦 Found {len(products)} products on page 1")
        
        # Analyze all groups
        group_counts = {}
        filter_results = {
            "total": len(products),
            "drivaksel": 0,
            "mellomaksel": 0,
            "other_groups": 0,
            "kept": 0,
            "filtered_out": 0
        }
        
        kept_products = []
        filtered_products = []
        
        print("\\n🔍 ANALYZING PRODUCTS:")
        print("-" * 60)
        
        for i, p in enumerate(products[:20], 1):  # Test first 20 products
            number = p.get("number", "N/A")
            name = p.get("name", "N/A")[:40]
            group_name = p.get("group", {}).get("name", "UNKNOWN")
            stock = p.get("available_quantity", 0)
            price = p.get("sales_price", 0)
            
            # Count groups
            group_counts[group_name] = group_counts.get(group_name, 0) + 1
            
            # Get i_nettbutikk
            i_nettbutikk = extract_custom_field(p, "i_nettbutikk").lower()
            
            # Test filter
            should_keep = filter_keep(p)
            
            # Update counters
            if group_name == "Drivaksel":
                filter_results["drivaksel"] += 1
            elif group_name == "Mellomaksel":
                filter_results["mellomaksel"] += 1
            else:
                filter_results["other_groups"] += 1
            
            if should_keep:
                filter_results["kept"] += 1
                kept_products.append({
                    "number": number,
                    "name": name,
                    "group": group_name,
                    "i_nettbutikk": i_nettbutikk,
                    "stock": stock,
                    "price": price
                })
            else:
                filter_results["filtered_out"] += 1
                filtered_products.append({
                    "number": number,
                    "name": name,
                    "group": group_name,
                    "i_nettbutikk": i_nettbutikk,
                    "stock": stock,
                    "price": price
                })
            
            # Print analysis
            status = "✅ KEEP" if should_keep else "🚫 FILTER"
            print(f"{i:2d}. {status} | {number:15s} | {group_name:12s} | i_nb:{i_nettbutikk:3s} | {name}")
        
        print("\\n" + "=" * 60)
        print("📊 FILTER ANALYSIS SUMMARY:")
        print("=" * 60)
        
        print(f"📦 Total products tested: {filter_results['total']}")
        print(f"🔧 Drivaksel products: {filter_results['drivaksel']}")
        print(f"🔧 Mellomaksel products: {filter_results['mellomaksel']}")
        print(f"❓ Other group products: {filter_results['other_groups']}")
        print()
        print(f"✅ Products KEPT: {filter_results['kept']}")
        print(f"🚫 Products FILTERED OUT: {filter_results['filtered_out']}")
        
        print("\\n📊 GROUP DISTRIBUTION:")
        for group, count in sorted(group_counts.items()):
            print(f"   {group}: {count} products")
        
        if kept_products:
            print("\\n✅ KEPT PRODUCTS:")
            for p in kept_products[:10]:  # Show first 10
                print(f"   ✅ {p['number']} ({p['group']}) - i_nb: {p['i_nettbutikk']}")
        
        if filtered_products:
            print("\\n🚫 FILTERED OUT PRODUCTS (sample):")
            for p in filtered_products[:10]:  # Show first 10
                print(f"   🚫 {p['number']} ({p['group']}) - i_nb: {p['i_nettbutikk']}")
        
        # Estimate total sync size
        if filter_results["kept"] > 0:
            estimated_total = (filter_results["kept"] / len(products)) * js.get("total", 0)
            print(f"\\n🎯 ESTIMATED TOTAL SYNC SIZE: {estimated_total:.0f} products")
            
            if estimated_total > 500:
                print("⚠️  WARNING: Estimated sync size is very large!")
                print("   This suggests the filter may not be working correctly.")
            elif estimated_total < 50:
                print("⚠️  WARNING: Estimated sync size is very small!")
                print("   This might be too restrictive.")
            else:
                print("✅ Estimated sync size looks reasonable.")
        
        return filter_results
        
    except Exception as e:
        print(f"❌ Error testing filter: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_specific_products():
    """Test filter on specific known products"""
    print("\\n🎯 TESTING SPECIFIC PRODUCTS:")
    print("=" * 50)
    
    # Test MA18002 specifically
    test_products = ["MA18002", "MA18001PT", "18-353040"]
    
    for product_number in test_products:
        print(f"\\n🔍 Testing {product_number}...")
        
        params = {
            "search": product_number,
            "fields": "number,name,sales_price,available_quantity,group,metadata",
            "limit": 10,
            "page": 1,
        }
        
        try:
            r = requests.get(RACKBEAT_API, headers=HEAD_RACK, params=params, timeout=30)
            r.raise_for_status()
            js = r.json()
            products = js.get("products", [])
            
            found = False
            for p in products:
                if p.get("number") == product_number:
                    found = True
                    group_name = p.get("group", {}).get("name", "UNKNOWN")
                    i_nettbutikk = extract_custom_field(p, "i_nettbutikk").lower()
                    should_keep = filter_keep(p)
                    
                    print(f"   ✅ Found: {product_number}")
                    print(f"   📊 Group: {group_name}")
                    print(f"   🌐 i_nettbutikk: '{i_nettbutikk}'")
                    print(f"   🎯 Filter result: {'KEEP' if should_keep else 'FILTER OUT'}")
                    
                    if not should_keep:
                        print(f"   ⚠️  WHY FILTERED: ", end="")
                        if group_name not in ["Drivaksel", "Mellomaksel"]:
                            print(f"Wrong group ({group_name})")
                        elif i_nettbutikk != "ja":
                            print(f"i_nettbutikk not 'ja' ('{i_nettbutikk}')")
                        else:
                            print("Unknown reason")
                    break
            
            if not found:
                print(f"   ❌ {product_number} not found in search results")
                
        except Exception as e:
            print(f"   ❌ Error testing {product_number}: {e}")

if __name__ == "__main__":
    print("🚀 STARTING FILTER DEBUG")
    print("=" * 60)
    
    # Test filter logic on sample
    results = test_filter_logic()
    
    # Test specific products
    test_specific_products()
    
    print("\\n🎉 FILTER DEBUG COMPLETED")
    print("=" * 60)
    
    if results and results["kept"] > 1000:
        print("⚠️  CRITICAL: Filter is keeping too many products!")
        print("   Review filter logic before running sync.")
    elif results and results["kept"] < 10:
        print("⚠️  WARNING: Filter is very restrictive.")
        print("   Verify this is expected behavior.")
    else:
        print("✅ Filter results look reasonable for testing.")
