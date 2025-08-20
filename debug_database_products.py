#!/usr/bin/env python3
"""
Debug database to check if products and metafields actually exist
"""

import os
from sqlalchemy import create_engine, text

def debug_database():
    """Check what's actually in the database"""
    
    print("🔍 DEBUGGING DATABASE CONTENTS")
    print("=" * 50)
    
    # Database connection
    DATABASE_URL = os.getenv('DATABASE_URL')
    if not DATABASE_URL:
        print("❌ No DATABASE_URL environment variable found")
        return
    
    try:
        engine = create_engine(DATABASE_URL)
        
        print("✅ Database connection established")
        
        # Check 1: Do we have any shopify_products?
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM shopify_products"))
            product_count = result.fetchone()[0]
            print(f"📦 Total shopify_products: {product_count}")
            
            if product_count == 0:
                print("❌ NO PRODUCTS IN DATABASE - This is the problem!")
                return
            
            # Check 2: Do we have any product_metafields?
            result = conn.execute(text("SELECT COUNT(*) FROM product_metafields"))
            metafield_count = result.fetchone()[0]
            print(f"🏷️  Total product_metafields: {metafield_count}")
            
            if metafield_count == 0:
                print("❌ NO METAFIELDS IN DATABASE - This is the problem!")
                return
            
            # Check 3: Do we have Original_nummer metafields?
            result = conn.execute(text("SELECT COUNT(*) FROM product_metafields WHERE key = 'Original_nummer'"))
            oem_count = result.fetchone()[0]
            print(f"🔢 Original_nummer metafields: {oem_count}")
            
            if oem_count == 0:
                print("❌ NO ORIGINAL_NUMMER METAFIELDS - This is the problem!")
                return
            
            # Check 4: Sample Original_nummer values
            result = conn.execute(text("SELECT value FROM product_metafields WHERE key = 'Original_nummer' AND value IS NOT NULL LIMIT 10"))
            oem_samples = [row[0] for row in result.fetchall()]
            print(f"🔍 Sample OEM values: {oem_samples[:5]}")
            
            # Check 5: Do we have product_group metafields?
            result = conn.execute(text("SELECT COUNT(*) FROM product_metafields WHERE key = 'product_group'"))
            group_count = result.fetchone()[0]
            print(f"📂 product_group metafields: {group_count}")
            
            # Check 6: What product groups exist?
            result = conn.execute(text("SELECT DISTINCT value FROM product_metafields WHERE key = 'product_group'"))
            groups = [row[0] for row in result.fetchall()]
            print(f"📋 Product groups: {groups}")
            
            # Check 7: Do we have Drivaksel/Mellomaksel products?
            result = conn.execute(text("""
                SELECT COUNT(*) FROM product_metafields 
                WHERE key = 'product_group' 
                AND value IN ('Drivaksel', 'Mellomaksel')
            """))
            target_count = result.fetchone()[0]
            print(f"🎯 Drivaksel/Mellomaksel products: {target_count}")
            
            if target_count == 0:
                print("❌ NO TARGET PRODUCTS (Drivaksel/Mellomaksel) - This is the problem!")
                return
            
            # Check 8: Test a simple OEM search
            test_oems = ["A2044102401", "2044102401", "30735120"]
            for test_oem in test_oems:
                result = conn.execute(text("""
                    SELECT COUNT(*) FROM product_metafields 
                    WHERE key = 'Original_nummer' 
                    AND value LIKE :pattern
                """), {"pattern": f"%{test_oem}%"})
                matches = result.fetchone()[0]
                print(f"🔍 OEM '{test_oem}' matches: {matches}")
            
            print(f"\n🎯 DATABASE DIAGNOSIS:")
            if product_count > 0 and oem_count > 0 and target_count > 0:
                print("✅ Database has products, metafields, and target groups")
                print("❓ Problem is likely in the search/matching logic")
            else:
                print("❌ Database is missing critical data")
                
    except Exception as e:
        print(f"❌ Database error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_database()
