#!/usr/bin/env python3
"""
Debug Metafields in Railway DB
Check what metafield keys exist and their values
"""

import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATABASE_URL = 'postgresql://postgres:pmTNRdLNPAwZTYvtBFsqvfmjUOoNEuqM@shinkansen.proxy.rlwy.net:13074/railway'

def debug_metafields():
    """Debug all metafields in Railway DB"""
    try:
        print("🔗 Connecting to Railway PostgreSQL...")
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # Get all unique metafield keys
        print("\n🔍 Getting all unique metafield keys...")
        cursor.execute("SELECT DISTINCT key, COUNT(*) FROM product_metafields GROUP BY key ORDER BY COUNT(*) DESC")
        keys = cursor.fetchall()
        
        print(f"📊 Found {len(keys)} unique metafield keys:")
        for key, count in keys:
            print(f"  - '{key}': {count} products")
        
        # Get sample metafields for each key
        print(f"\n🔍 Sample values for each key:")
        for key, count in keys[:10]:  # Show top 10 keys
            cursor.execute("SELECT value FROM product_metafields WHERE key = %s LIMIT 5", (key,))
            values = cursor.fetchall()
            print(f"\n  Key '{key}' sample values:")
            for value in values:
                print(f"    - '{value[0]}'")
        
        # Look specifically for group-related keys
        print(f"\n🎯 Looking for group-related metafields...")
        group_keys = ['group', 'Group', 'product_group', 'rackbeat_group', 'category', 'Category']
        
        for group_key in group_keys:
            cursor.execute("SELECT COUNT(*), array_agg(DISTINCT value) FROM product_metafields WHERE key = %s", (group_key,))
            result = cursor.fetchone()
            count, values = result
            if count > 0:
                print(f"  ✅ Found '{group_key}': {count} products")
                print(f"     Values: {values}")
            else:
                print(f"  ❌ No '{group_key}' found")
        
        # Get products with their metafields
        print(f"\n📦 Sample products with all their metafields:")
        cursor.execute("""
        SELECT sp.id, sp.title, 
               array_agg(pm.key || '=' || pm.value) as metafields
        FROM shopify_products sp
        LEFT JOIN product_metafields pm ON sp.id = pm.product_id
        GROUP BY sp.id, sp.title
        LIMIT 5
        """)
        
        products = cursor.fetchall()
        for product_id, title, metafields in products:
            print(f"\n  Product: {title[:50]}...")
            print(f"    ID: {product_id}")
            if metafields and metafields[0]:
                for metafield in metafields:
                    if metafield and metafield != 'None':
                        print(f"    - {metafield}")
            else:
                print(f"    - No metafields")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Database error: {e}")

if __name__ == "__main__":
    debug_metafields()
