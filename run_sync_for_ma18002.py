#!/usr/bin/env python3
"""
Direct sync script to get MA18002 into Shopify database
"""

import os
import sys

# Set environment variables for Railway database
os.environ['DATABASE_URL'] = 'postgresql://postgres:bNrAgtVDLbFWrqp@junction.proxy.rlwy.net:47292/railway'

def run_sync_for_ma18002():
    """Run sync to get MA18002 into Shopify database"""
    print("🔄 RUNNING SYNC TO GET MA18002 INTO SHOPIFY")
    print("=" * 50)
    
    try:
        # Import sync functions
        from sync_service import fetch_all_rackbeat, filter_keep, map_to_shop_payload, create_or_update_product_optimized
        from database import init_db
        
        print("✅ Imported sync functions successfully")
        
        # Initialize database
        print("🔧 Initializing database...")
        init_db()
        print("✅ Database initialized")
        
        # Fetch all Rackbeat products
        print("📡 Fetching all products from Rackbeat...")
        all_products = fetch_all_rackbeat()
        print(f"✅ Fetched {len(all_products)} products from Rackbeat")
        
        # Filter for eligible products
        print("🔍 Filtering for eligible products...")
        eligible_products = [p for p in all_products if filter_keep(p)]
        print(f"✅ Found {len(eligible_products)} eligible products")
        
        # Look for MA18002 specifically
        ma18002_found = False
        for product in eligible_products:
            if product.get('number') == 'MA18002':
                ma18002_found = True
                print(f"🎯 FOUND MA18002 in eligible products!")
                print(f"   Name: {product.get('name', 'N/A')}")
                print(f"   Group: {product.get('group', {}).get('name', 'N/A')}")
                print(f"   Stock: {product.get('available_quantity', 0)}")
                print(f"   Price: {product.get('sales_price', 0)}")
                
                # Check metadata for OEMs
                metadata = product.get('metadata', [])
                for field in metadata:
                    if field.get('slug') == 'original-nummer':
                        oem_value = field.get('value', '')
                        print(f"   OEMs: {oem_value[:100]}...")
                        
                        # Check for Nissan OEMs
                        nissan_patterns = ['370008H310', '370008H510', '370008H800', '37000-8H310', '37000-8H510', '37000-8H800']
                        found_nissan = [pattern for pattern in nissan_patterns if pattern in oem_value]
                        if found_nissan:
                            print(f"   🎯 CONTAINS NISSAN OEMs: {found_nissan}")
                        else:
                            print(f"   ❌ NO NISSAN OEMs found")
                
                # Sync MA18002 to Shopify
                print(f"🔄 Syncing MA18002 to Shopify...")
                payload, metafields = map_to_shop_payload(product)
                result = create_or_update_product_optimized(payload, metafields)
                
                if result:
                    print(f"✅ MA18002 synced successfully! Product ID: {result}")
                    print(f"🎉 MA18002 should now be searchable by OEM numbers!")
                else:
                    print(f"❌ Failed to sync MA18002")
                
                break
        
        if not ma18002_found:
            print(f"❌ MA18002 NOT FOUND in eligible products!")
            print(f"💡 This means MA18002 is filtered out by sync rules")
            
            # Check if MA18002 exists at all in Rackbeat
            ma18002_in_rackbeat = False
            for product in all_products:
                if product.get('number') == 'MA18002':
                    ma18002_in_rackbeat = True
                    print(f"🔍 FOUND MA18002 in Rackbeat but FILTERED OUT:")
                    print(f"   Name: {product.get('name', 'N/A')}")
                    print(f"   Group: {product.get('group', {}).get('name', 'N/A')}")
                    print(f"   Stock: {product.get('available_quantity', 0)}")
                    print(f"   Price: {product.get('sales_price', 0)}")
                    
                    # Check why it's filtered out
                    print(f"\\n🔍 FILTER ANALYSIS:")
                    if product.get('available_quantity', 0) < 1:
                        print(f"   ❌ Stock too low: {product.get('available_quantity', 0)}")
                    if product.get('sales_price', 0) <= 0:
                        print(f"   ❌ Price too low: {product.get('sales_price', 0)}")
                    
                    group_name = product.get('group', {}).get('name', '')
                    if group_name not in ['Drivaksel', 'Mellomaksel']:
                        print(f"   ❌ Wrong group: {group_name}")
                    
                    # Check i_nettbutikk
                    from sync_service import extract_custom_field
                    i_nettbutikk = extract_custom_field(product, 'i_nettbutikk')
                    if i_nettbutikk.lower() != 'ja':
                        print(f"   ❌ i_nettbutikk not 'ja': '{i_nettbutikk}'")
                        print(f"   💡 This is likely the main blocker!")
                    
                    break
            
            if not ma18002_in_rackbeat:
                print(f"❌ MA18002 NOT FOUND in Rackbeat at all!")
                print(f"💡 Product may not exist or API access issues")
        
        print(f"\\n🎯 SYNC SUMMARY:")
        print(f"   Total products in Rackbeat: {len(all_products)}")
        print(f"   Eligible for sync: {len(eligible_products)}")
        print(f"   MA18002 found and synced: {ma18002_found}")
        
        if ma18002_found:
            print(f"\\n🚀 NEXT STEP: Test search!")
            print(f"   Try searching for '370008H310' in webshop")
            print(f"   Should now return MA18002!")
        
    except Exception as e:
        print(f"❌ Sync error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_sync_for_ma18002()
