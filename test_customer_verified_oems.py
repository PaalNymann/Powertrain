#!/usr/bin/env python3
"""
Test Customer-Verified OEMs for ZT41818 (Nissan X-Trail)
Direct database testing to find why MA18002 is not matched
"""

import os
import sys
import requests
from database import SessionLocal, ProductMetafield, ShopifyProduct
from sqlalchemy import text

def test_customer_verified_oems():
    """Test customer-verified OEMs directly in production database"""
    
    # Customer-verified OEMs for ZT41818 (Nissan X-Trail) / MA18002
    customer_oems = [
        '370008H310',  # Primary customer-verified OEM
        '370008H510',  # Secondary customer-verified OEM  
        '370008H800',  # Tertiary customer-verified OEM
        '37000-8H310', # Alternative format with dash
        '37000-8H510', # Alternative format with dash
        '37000-8H800'  # Alternative format with dash
    ]
    
    print("🎯 TESTING CUSTOMER-VERIFIED OEMS FOR ZT41818 (NISSAN X-TRAIL)")
    print("=" * 70)
    
    # Test each OEM against production database
    for oem in customer_oems:
        print(f"\n🔍 Testing OEM: {oem}")
        test_oem_in_database(oem)

def test_oem_in_database(oem_number):
    """Test individual OEM in production database with comprehensive variations"""
    
    session = SessionLocal()
    try:
        # Generate OEM variations for comprehensive testing
        oem_variations = [
            oem_number,                                    # Original: "370008H310"
            oem_number.upper(),                           # Upper: "370008H310"
            oem_number.lower(),                           # Lower: "370008h310"
            ''.join(oem_number.split()),                  # No spaces: "370008H310"
            ''.join(oem_number.split()).upper(),          # No spaces upper: "370008H310"
            ''.join(oem_number.split()).lower(),          # No spaces lower: "370008h310"
            oem_number.replace('-', ''),                  # No dashes: "370008H310"
            oem_number.replace('-', '').replace(' ', ''), # No dashes/spaces: "370008H310"
            oem_number.replace(' ', '-'),                 # Spaces to dashes: "370008H310"
            oem_number.replace('-', ' '),                 # Dashes to spaces: "37000 8H310"
        ]
        
        # Remove duplicates while preserving order
        seen = set()
        unique_variations = []
        for var in oem_variations:
            if var not in seen:
                seen.add(var)
                unique_variations.append(var)
        
        print(f"   🔧 Testing {len(unique_variations)} variations")
        
        total_matches = 0
        
        for variation in unique_variations:
            # Test comma-separated OEM matching
            comma_query = text("""
                SELECT COUNT(*) FROM product_metafields 
                WHERE key = 'Original_nummer' 
                AND (
                    value LIKE :oem_start OR 
                    value LIKE :oem_middle OR 
                    value LIKE :oem_end OR
                    value = :oem_exact
                )
            """)
            
            result = session.execute(comma_query, {
                'oem_start': f'{variation},%',      # OEM at start: "370008H310, ..."
                'oem_middle': f'%, {variation},%',  # OEM in middle: "..., 370008H310, ..."
                'oem_end': f'%, {variation}',       # OEM at end: "..., 370008H310"
                'oem_exact': variation              # Exact match (single OEM)
            })
            
            count = result.scalar()
            if count > 0:
                print(f"   ✅ MATCH FOUND: {count} products for variation '{variation}'")
                total_matches += count
                
                # Get sample products for this variation
                products_query = text("""
                    SELECT sp.id, sp.title, sp.handle, sp.sku, pm.value 
                    FROM shopify_products sp
                    INNER JOIN product_metafields pm ON sp.id = pm.product_id
                    WHERE pm.key = 'Original_nummer' 
                    AND (
                        pm.value LIKE :oem_start OR 
                        pm.value LIKE :oem_middle OR 
                        pm.value LIKE :oem_end OR
                        pm.value = :oem_exact
                    )
                    LIMIT 3
                """)
                
                products_result = session.execute(products_query, {
                    'oem_start': f'{variation},%',
                    'oem_middle': f'%, {variation},%',
                    'oem_end': f'%, {variation}',
                    'oem_exact': variation
                })
                
                products = products_result.fetchall()
                for product in products:
                    print(f"      📦 Product: {product[1]} (SKU: {product[3]}, OEMs: {product[4]})")
        
        if total_matches == 0:
            print(f"   ❌ NO MATCHES: OEM {oem_number} not found in any variation")
        else:
            print(f"   ✅ TOTAL MATCHES: {total_matches} products found for OEM {oem_number}")
            
    except Exception as e:
        print(f"   ❌ ERROR testing OEM {oem_number}: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

def check_ma18002_in_database():
    """Check if MA18002 exists in the database"""
    print("\n🔍 CHECKING MA18002 IN DATABASE")
    print("=" * 40)
    
    session = SessionLocal()
    try:
        # Search for MA18002 by SKU/handle/title
        ma18002_query = text("""
            SELECT sp.id, sp.title, sp.handle, sp.sku, sp.price, sp.inventory_quantity
            FROM shopify_products sp
            WHERE sp.sku LIKE '%MA18002%' 
               OR sp.handle LIKE '%ma18002%'
               OR sp.title LIKE '%MA18002%'
        """)
        
        result = session.execute(ma18002_query)
        products = result.fetchall()
        
        if products:
            print(f"✅ MA18002 FOUND: {len(products)} products in database")
            for product in products:
                print(f"   📦 {product[1]} (SKU: {product[3]}, Price: {product[4]}, Stock: {product[5]})")
                
                # Get OEM metafields for this product
                oem_query = text("""
                    SELECT value FROM product_metafields 
                    WHERE product_id = :product_id AND key = 'Original_nummer'
                """)
                oem_result = session.execute(oem_query, {'product_id': product[0]})
                oem_value = oem_result.scalar()
                
                if oem_value:
                    print(f"      🔗 OEMs: {oem_value}")
                else:
                    print(f"      ❌ No OEM metafields found")
        else:
            print("❌ MA18002 NOT FOUND in database")
            print("   This explains why ZT41818 returns 0 parts - MA18002 is missing!")
            
    except Exception as e:
        print(f"❌ ERROR checking MA18002: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

def main():
    """Main test function"""
    print("🎯 CUSTOMER-VERIFIED OEM TESTING FOR ZT41818")
    print("Testing why Nissan X-Trail returns 0 parts despite seed OEM strategy")
    print("=" * 80)
    
    # First check if MA18002 exists in database
    check_ma18002_in_database()
    
    # Then test customer-verified OEMs
    test_customer_verified_oems()
    
    print("\n" + "=" * 80)
    print("🎯 SUMMARY:")
    print("   1. If MA18002 is missing: Need to debug sync pipeline")
    print("   2. If OEMs don't match: Need to debug OEM normalization")
    print("   3. If both exist but no match: Need to debug search logic")

if __name__ == "__main__":
    main()
