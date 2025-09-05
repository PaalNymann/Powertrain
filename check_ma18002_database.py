#!/usr/bin/env python3
"""
Check MA18002 and OEMs directly in Railway PostgreSQL database
"""

import os
from dotenv import load_dotenv
load_dotenv()

# Import database functions
from database import SessionLocal, ShopifyProduct, ProductMetafield

def check_ma18002_in_database():
    """Check if MA18002 exists in Railway database with OEMs"""
    print("🔍 CHECKING MA18002 IN RAILWAY DATABASE")
    print("=" * 45)
    
    session = SessionLocal()
    try:
        # Search for MA18002 in shopify_products table
        ma18002 = session.query(ShopifyProduct).filter(
            ShopifyProduct.sku == "MA18002"
        ).first()
        
        if ma18002:
            print(f"✅ FOUND MA18002 in Railway database!")
            print(f"   SKU: {ma18002.sku}")
            print(f"   Title: {ma18002.title}")
            print(f"   Product Group: {ma18002.product_group}")
            print(f"   Price: {ma18002.price}")
            print(f"   Stock: {ma18002.available_quantity}")
            
            # Check for Original_nummer metafield
            original_nummer_metafield = session.query(ProductMetafield).filter(
                ProductMetafield.product_id == ma18002.id,
                ProductMetafield.key == "Original_nummer"
            ).first()
            
            if original_nummer_metafield:
                oem_numbers = original_nummer_metafield.value
                print(f"\n🔑 ORIGINAL_NUMMER METAFIELD:")
                print(f"   Value: {oem_numbers}")
                
                # Parse OEM numbers (comma-separated)
                if oem_numbers:
                    oem_list = [oem.strip() for oem in oem_numbers.split(',')]
                    print(f"   Parsed OEMs ({len(oem_list)}):")
                    for i, oem in enumerate(oem_list[:10]):  # Show first 10
                        print(f"     {i+1}. {oem}")
                    
                    # Check for expected Nissan OEMs
                    expected_nissan_oems = [
                        "37000-8H310", "37000-8H510", "37000-8H800",
                        "370008H310", "370008H510", "370008H800"
                    ]
                    
                    found_nissan_oems = []
                    for expected_oem in expected_nissan_oems:
                        for actual_oem in oem_list:
                            if expected_oem in actual_oem or actual_oem in expected_oem:
                                found_nissan_oems.append(actual_oem)
                    
                    if found_nissan_oems:
                        print(f"\n🎯 FOUND EXPECTED NISSAN OEMs:")
                        for oem in found_nissan_oems:
                            print(f"     ✅ {oem}")
                        print(f"\n💡 MA18002 has correct Nissan OEMs in database!")
                        print(f"💡 If TecDoc returns these OEMs for ZT41818, it should match!")
                    else:
                        print(f"\n❌ NO EXPECTED NISSAN OEMs FOUND")
                        print(f"💡 Database OEMs don't match expected Nissan format")
                        print(f"💡 This explains why ZT41818 doesn't find MA18002")
                else:
                    print(f"\n❌ Original_nummer metafield is empty!")
            else:
                print(f"\n❌ NO Original_nummer metafield found!")
                print(f"💡 This explains why MA18002 can't be matched by OEM")
        else:
            print(f"❌ MA18002 NOT FOUND in Railway database!")
            print(f"💡 Product is not synced to Shopify")
            print(f"💡 This explains why ZT41818 search returns 0 results")
            
            # Check if any Mellomaksel products exist
            mellomaksel_count = session.query(ShopifyProduct).filter(
                ShopifyProduct.product_group == "Mellomaksel"
            ).count()
            print(f"\n📊 Total Mellomaksel products in database: {mellomaksel_count}")
            
            if mellomaksel_count == 0:
                print(f"💡 NO Mellomaksel products synced - sync pipeline issue!")
            else:
                print(f"💡 Other Mellomaksel products exist - MA18002 specifically missing")
        
        # General database stats
        total_products = session.query(ShopifyProduct).count()
        total_metafields = session.query(ProductMetafield).count()
        original_nummer_metafields = session.query(ProductMetafield).filter(
            ProductMetafield.key == "Original_nummer"
        ).count()
        
        print(f"\n📊 DATABASE STATS:")
        print(f"   Total products: {total_products}")
        print(f"   Total metafields: {total_metafields}")
        print(f"   Original_nummer metafields: {original_nummer_metafields}")
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

def check_tecdoc_oems_in_database():
    """Check if any TecDoc OEMs for ZT41818 exist in database"""
    print(f"\n🔍 CHECKING TECDOC OEMs IN DATABASE")
    print("=" * 40)
    
    # These are the OEMs that TecDoc should return for ZT41818
    # (based on previous debugging - backend finds 4 OEMs)
    # We need to check if ANY of these exist in the database
    
    session = SessionLocal()
    try:
        # Get all Original_nummer metafields to search through
        all_metafields = session.query(ProductMetafield).filter(
            ProductMetafield.key == "Original_nummer"
        ).all()
        
        print(f"📋 Searching through {len(all_metafields)} Original_nummer metafields...")
        
        # Common Nissan OEM patterns to look for
        nissan_patterns = [
            "37000", "8H310", "8H510", "8H800", 
            "370008H310", "370008H510", "370008H800"
        ]
        
        matching_products = []
        for metafield in all_metafields:
            oem_value = metafield.value or ""
            for pattern in nissan_patterns:
                if pattern in oem_value:
                    # Get the product for this metafield
                    product = session.query(ShopifyProduct).filter(
                        ShopifyProduct.id == metafield.product_id
                    ).first()
                    if product:
                        matching_products.append({
                            'sku': product.sku,
                            'title': product.title,
                            'group': product.product_group,
                            'oems': oem_value,
                            'pattern': pattern
                        })
                    break
        
        if matching_products:
            print(f"\n🎯 FOUND {len(matching_products)} PRODUCTS WITH NISSAN OEMs:")
            for i, product in enumerate(matching_products[:10]):  # Show first 10
                print(f"   {i+1}. {product['sku']}: {product['title'][:40]}")
                print(f"      Group: {product['group']}")
                print(f"      Pattern: {product['pattern']}")
                print(f"      OEMs: {product['oems'][:60]}...")
                print()
            
            # Check if MA18002 is among them
            ma18002_in_results = any(p['sku'] == 'MA18002' for p in matching_products)
            if ma18002_in_results:
                print(f"✅ MA18002 is among the Nissan OEM products!")
            else:
                print(f"❌ MA18002 NOT among the Nissan OEM products")
                print(f"💡 MA18002 may have different OEM format")
        else:
            print(f"❌ NO PRODUCTS found with Nissan OEM patterns!")
            print(f"💡 Either no Nissan products synced or different OEM format")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    check_ma18002_in_database()
    check_tecdoc_oems_in_database()
