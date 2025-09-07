#!/usr/bin/env python3
"""
Test script to check database OEM metafields and MA18002 presence
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add the current directory to Python path
sys.path.append('/Users/nyman/powertrain_system')

def test_database_oems():
    """Test database OEM metafields and MA18002 presence"""
    
    # Use Railway PostgreSQL connection
    DATABASE_URL = "postgresql://postgres:bRAKTdJOLAOmZNTSKHKNZAjBNnGxPNLY@junction.proxy.rlwy.net:36247/railway"
    
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    try:
        print("🔍 TESTING DATABASE OEM METAFIELDS AND MA18002 PRESENCE")
        print("=" * 60)
        
        # Test 1: Check if Original_nummer metafields exist
        print("\n📊 Test 1: Checking Original_nummer metafields...")
        count_query = text("SELECT COUNT(*) FROM product_metafields WHERE key = 'Original_nummer'")
        count_result = session.execute(count_query)
        total_oem_metafields = count_result.scalar()
        print(f"   Total Original_nummer metafields: {total_oem_metafields}")
        
        if total_oem_metafields == 0:
            print("   ❌ CRITICAL: No Original_nummer metafields found!")
            print("   This explains why no OEM matching works!")
            return
        
        # Test 2: Check sample OEM values
        print("\n🔍 Test 2: Sample OEM values in database...")
        sample_query = text("SELECT value FROM product_metafields WHERE key = 'Original_nummer' AND value IS NOT NULL LIMIT 10")
        sample_result = session.execute(sample_query)
        sample_oems = [row[0] for row in sample_result.fetchall()]
        print(f"   Sample OEM values: {sample_oems}")
        
        # Test 3: Search for MA18002 specifically
        print("\n🔍 Test 3: Searching for MA18002...")
        ma18002_query = text("SELECT id, title, handle, sku FROM shopify_products WHERE sku = 'MA18002' OR title LIKE '%MA18002%'")
        ma18002_result = session.execute(ma18002_query)
        ma18002_products = ma18002_result.fetchall()
        
        if ma18002_products:
            print(f"   ✅ Found MA18002: {len(ma18002_products)} products")
            for product in ma18002_products:
                print(f"      ID: {product[0]}, Title: {product[1]}, SKU: {product[3]}")
                
                # Get OEMs for this product
                oem_query = text("SELECT value FROM product_metafields WHERE product_id = :product_id AND key = 'Original_nummer'")
                oem_result = session.execute(oem_query, {'product_id': product[0]})
                oem_values = [row[0] for row in oem_result.fetchall()]
                print(f"      OEMs: {oem_values}")
        else:
            print("   ❌ MA18002 not found in database!")
        
        # Test 4: Search for customer-verified Nissan X-Trail OEMs
        print("\n🔍 Test 4: Searching for customer-verified Nissan X-Trail OEMs...")
        nissan_oems = ['370008H310', '370008H510', '370008H800', '37000-8H310', '37000-8H510', '37000-8H800']
        
        for oem in nissan_oems:
            # Search for this OEM in metafields
            oem_search_query = text("""
                SELECT sp.id, sp.title, sp.sku, pm.value 
                FROM shopify_products sp
                INNER JOIN product_metafields pm ON sp.id = pm.product_id
                WHERE pm.key = 'Original_nummer' 
                AND (
                    pm.value LIKE :oem_start OR 
                    pm.value LIKE :oem_middle OR 
                    pm.value LIKE :oem_end OR
                    pm.value = :oem_exact
                )
                LIMIT 5
            """)
            oem_result = session.execute(oem_search_query, {
                'oem_start': f'{oem},%',
                'oem_middle': f'%, {oem},%',
                'oem_end': f'%, {oem}',
                'oem_exact': oem
            })
            oem_products = oem_result.fetchall()
            
            if oem_products:
                print(f"   ✅ OEM {oem}: Found {len(oem_products)} products")
                for product in oem_products:
                    print(f"      {product[2]} - {product[1]}")
            else:
                print(f"   ❌ OEM {oem}: No products found")
        
        # Test 5: Check what metafield keys exist
        print("\n📋 Test 5: Available metafield keys...")
        keys_query = text("SELECT DISTINCT key FROM product_metafields LIMIT 20")
        keys_result = session.execute(keys_query)
        existing_keys = [row[0] for row in keys_result.fetchall()]
        print(f"   Available keys: {existing_keys}")
        
        print("\n" + "=" * 60)
        print("🎯 DATABASE OEM TEST COMPLETE")
        
    except Exception as e:
        print(f"❌ Database test error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    test_database_oems()
