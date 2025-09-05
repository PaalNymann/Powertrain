#!/usr/bin/env python3
"""
Precise filter test to count EXACTLY how many products should be synced
- ONLY group: Drivaksel OR Mellomaksel
- ONLY i_nettbutikk: ja (exact match)
"""

import os
import sys
import requests
from dotenv import load_dotenv
load_dotenv()

# ---------- ENV ----------
RACKBEAT_API = os.getenv("RACKBEAT_ENDPOINT", "https://app.rackbeat.com/api/products")
RACKBEAT_KEY = os.getenv("RACKBEAT_API_KEY")

HEAD_RACK = {
    "Authorization": f"Bearer {RACKBEAT_KEY}",
    "Content-Type": "application/json"
}

def get_i_nettbutikk_from_metadata(metadata):
    """Extract i_nettbutikk from metadata array - EXACT implementation"""
    # Test different possible slug names (case-insensitive)
    possible_slugs = ['i-nettbutikk', 'i_nettbutikk', 'nettbutikk', 'webshop', 'online']
    for field in metadata:
        slug = field.get('slug', '').lower()  # Convert to lowercase for comparison
        if slug in possible_slugs:
            value = field.get('value', '').lower().strip()  # Also normalize value
            return value
    return ''

def precise_filter_test():
    """Test filter with EXACT criteria and count eligible products"""
    print("🎯 PRECISE FILTER TEST")
    print("=" * 50)
    print("✅ CRITERIA:")
    print("   - Group: EXACTLY 'Drivaksel' OR 'Mellomaksel'")
    print("   - i_nettbutikk: EXACTLY 'ja' (case-insensitive)")
    print("   - NO other criteria")
    print()
    
    # Get first few pages to test
    total_products = 0
    eligible_products = []
    group_stats = {}
    i_nettbutikk_stats = {}
    
    # Test first 5 pages to get a good sample
    for page in range(1, 6):
        print(f"📥 Testing page {page}...")
        
        params = {
            "limit": 250,
            "page": page,
            "fields": "number,name,sales_price,available_quantity,group,metadata"
        }
        
        try:
            r = requests.get(RACKBEAT_API, headers=HEAD_RACK, params=params, timeout=30)
            r.raise_for_status()
            js = r.json()
            products = js.get("products", [])
            
            if not products:
                print(f"   📄 No products on page {page}")
                break
            
            total_products += len(products)
            print(f"   📦 Found {len(products)} products")
            
            for p in products:
                # Check group
                group_name = p.get("group", {}).get("name", "")
                group_stats[group_name] = group_stats.get(group_name, 0) + 1
                
                # Check i_nettbutikk
                i_nettbutikk = get_i_nettbutikk_from_metadata(p.get("metadata", []))
                i_nettbutikk_stats[i_nettbutikk] = i_nettbutikk_stats.get(i_nettbutikk, 0) + 1
                
                # Apply EXACT filter
                if group_name in ["Drivaksel", "Mellomaksel"] and i_nettbutikk == "ja":
                    eligible_products.append({
                        "number": p.get("number", "N/A"),
                        "name": p.get("name", "N/A")[:40],
                        "group": group_name,
                        "i_nettbutikk": i_nettbutikk,
                        "stock": p.get("available_quantity", 0),
                        "price": p.get("sales_price", 0)
                    })
            
        except Exception as e:
            print(f"❌ Error on page {page}: {e}")
            break
    
    print(f"\\n📊 SAMPLE ANALYSIS ({total_products} products tested):")
    print("=" * 50)
    
    print(f"✅ ELIGIBLE PRODUCTS: {len(eligible_products)}")
    
    # Estimate total
    if total_products > 0:
        estimated_total = (len(eligible_products) / total_products) * 10000  # Assume ~10k total products
        print(f"🎯 ESTIMATED TOTAL ELIGIBLE: {estimated_total:.0f} products")
        
        if estimated_total > 200:
            print("⚠️  WARNING: This seems high for only Drivaksel/Mellomaksel with i_nettbutikk: ja")
        elif estimated_total < 50:
            print("⚠️  This seems low - might be missing some products")
        else:
            print("✅ This seems reasonable")
    
    print(f"\\n📊 GROUP DISTRIBUTION (sample):")
    for group, count in sorted(group_stats.items()):
        status = "✅" if group in ["Drivaksel", "Mellomaksel"] else "❌"
        print(f"   {status} {group}: {count} products")
    
    print(f"\\n📊 I_NETTBUTIKK DISTRIBUTION (sample):")
    for value, count in sorted(i_nettbutikk_stats.items()):
        status = "✅" if value == "ja" else "❌"
        print(f"   {status} '{value}': {count} products")
    
    print(f"\\n✅ ELIGIBLE PRODUCTS (first 20):")
    for i, p in enumerate(eligible_products[:20], 1):
        print(f"   {i:2d}. {p['number']:15s} | {p['group']:12s} | {p['name']}")
    
    if len(eligible_products) > 20:
        print(f"   ... and {len(eligible_products) - 20} more")
    
    # Test specific products
    print(f"\\n🎯 TESTING SPECIFIC PRODUCTS:")
    test_products = ["MA18002", "MA18001PT", "18-353040"]
    
    for product_number in test_products:
        found = False
        for p in eligible_products:
            if p['number'] == product_number:
                found = True
                print(f"   ✅ {product_number}: Found in eligible list")
                break
        
        if not found:
            print(f"   ❌ {product_number}: NOT in eligible list")
            
            # Search for it specifically
            params = {
                "search": product_number,
                "fields": "number,name,group,metadata",
                "limit": 10,
                "page": 1,
            }
            
            try:
                r = requests.get(RACKBEAT_API, headers=HEAD_RACK, params=params, timeout=30)
                r.raise_for_status()
                js = r.json()
                products = js.get("products", [])
                
                for p in products:
                    if p.get("number") == product_number:
                        group_name = p.get("group", {}).get("name", "")
                        i_nb = get_i_nettbutikk_from_metadata(p.get("metadata", []))
                        print(f"      Found: Group='{group_name}', i_nettbutikk='{i_nb}'")
                        
                        if group_name not in ["Drivaksel", "Mellomaksel"]:
                            print(f"      ❌ Wrong group: '{group_name}'")
                        elif i_nb != "ja":
                            print(f"      ❌ Wrong i_nettbutikk: '{i_nb}'")
                        else:
                            print(f"      ⚠️  Should be eligible but not found in sample")
                        break
                
            except Exception as e:
                print(f"      ❌ Error searching: {e}")
    
    return len(eligible_products), estimated_total

if __name__ == "__main__":
    eligible_count, estimated_total = precise_filter_test()
    
    print(f"\\n🎉 PRECISE FILTER TEST COMPLETED")
    print("=" * 50)
    print(f"📊 Sample eligible: {eligible_count}")
    print(f"🎯 Estimated total: {estimated_total:.0f}")
    
    if estimated_total > 300:
        print("\\n⚠️  CRITICAL: Too many products!")
        print("   Filter logic needs to be more restrictive.")
    elif estimated_total < 20:
        print("\\n⚠️  WARNING: Very few products!")
        print("   Verify this is expected.")
    else:
        print("\\n✅ Product count looks reasonable for sync.")
