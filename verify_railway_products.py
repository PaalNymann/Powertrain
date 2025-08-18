#!/usr/bin/env python3
"""
Verify Railway Database Products
Check which products are actually in Railway PostgreSQL database
"""

import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATABASE_URL = 'postgresql://postgres:pmTNRdLNPAwZTYvtBFsqvfmjUOoNEuqM@shinkansen.proxy.rlwy.net:13074/railway'

def verify_railway_products():
    """Check all products in Railway PostgreSQL database"""
    try:
        print("🔗 Connecting to Railway PostgreSQL...")
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # Get all products with their details
        query = """
        SELECT sp.id, sp.title, sp.handle, sp.sku
        FROM shopify_products sp
        ORDER BY sp.title
        """
        
        cursor.execute(query)
        products = cursor.fetchall()
        
        print(f"\n📊 RAILWAY DATABASE PRODUCTS ({len(products)} total):")
        print("=" * 80)
        
        drivaksel_count = 0
        mellomaksel_count = 0
        other_count = 0
        
        for product_id, title, handle, sku in products:
            if 'drivaksel' in title.lower() or 'drivaksel' in handle.lower():
                print(f"🔧 DRIVAKSEL: {product_id} - {title}")
                drivaksel_count += 1
            elif 'mellomaksel' in title.lower() or 'mellomaksel' in handle.lower():
                print(f"⚙️  MELLOMAKSEL: {product_id} - {title}")
                mellomaksel_count += 1
            else:
                print(f"❓ OTHER: {product_id} - {title}")
                other_count += 1
        
        print("=" * 80)
        print(f"📈 SUMMARY:")
        print(f"  Drivaksel products: {drivaksel_count}")
        print(f"  Mellomaksel products: {mellomaksel_count}")
        print(f"  Other products: {other_count}")
        print(f"  Total products: {len(products)}")
        
        # Also check metafields
        print(f"\n🔍 CHECKING METAFIELDS...")
        cursor.execute("""
        SELECT COUNT(DISTINCT product_id) 
        FROM product_metafields 
        WHERE key = 'Original_nummer'
        """)
        metafield_count = cursor.fetchone()[0]
        print(f"  Products with Original_nummer metafield: {metafield_count}")
        
        cursor.close()
        conn.close()
        
        return {
            'total': len(products),
            'drivaksel': drivaksel_count,
            'mellomaksel': mellomaksel_count,
            'other': other_count,
            'metafields': metafield_count
        }
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        return None

if __name__ == "__main__":
    result = verify_railway_products()
    
    if result:
        print(f"\n🎯 VERIFICATION COMPLETE!")
        if result['drivaksel'] + result['mellomaksel'] > 0:
            print(f"✅ Found {result['drivaksel'] + result['mellomaksel']} Drivaksel/Mellomaksel products in Railway DB")
        else:
            print(f"⚠️  No Drivaksel/Mellomaksel products found in Railway DB!")
    else:
        print(f"❌ Verification failed!")
