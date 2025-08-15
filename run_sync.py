#!/usr/bin/env python3
"""
Simple script to run the fixed sync and verify results
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from direct_postgresql_sync import main as sync_main
import psycopg2
from dotenv import load_dotenv

def check_database():
    """Check database contents after sync"""
    load_dotenv()
    DATABASE_URL = os.getenv('DATABASE_URL')
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # Count products
        cursor.execute('SELECT COUNT(*) FROM shopify_products')
        products_count = cursor.fetchone()[0]
        
        # Count metafields
        cursor.execute('SELECT COUNT(*) FROM product_metafields')
        metafields_count = cursor.fetchone()[0]
        
        # Check for Original_nummer metafields
        cursor.execute("SELECT COUNT(*) FROM product_metafields WHERE key = 'Original_nummer'")
        oem_count = cursor.fetchone()[0]
        
        # Check for specific Volvo OEM
        cursor.execute("SELECT COUNT(*) FROM product_metafields WHERE key = 'Original_nummer' AND value LIKE '%30735120%'")
        volvo_oem_count = cursor.fetchone()[0]
        
        print(f"📊 DATABASE STATUS:")
        print(f"   Products: {products_count}")
        print(f"   Metafields: {metafields_count}")
        print(f"   Original_nummer fields: {oem_count}")
        print(f"   Volvo OEM (30735120): {volvo_oem_count}")
        
        if products_count > 200:
            print("❌ TOO MANY PRODUCTS! Should be ~155")
        elif products_count < 100:
            print("❌ TOO FEW PRODUCTS! Should be ~155")
        else:
            print("✅ Product count looks good!")
            
        if oem_count == 0:
            print("❌ NO Original_nummer metafields found!")
        else:
            print("✅ Original_nummer metafields found!")
            
        conn.close()
        
    except Exception as e:
        print(f"❌ Database error: {e}")

if __name__ == "__main__":
    print("🚀 RUNNING FIXED SYNC...")
    
    # Clear database first
    load_dotenv()
    DATABASE_URL = os.getenv('DATABASE_URL')
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        print("🗑️ Clearing old data...")
        cursor.execute('DELETE FROM product_metafields')
        cursor.execute('DELETE FROM shopify_products')
        conn.commit()
        conn.close()
        print("✅ Database cleared")
    except Exception as e:
        print(f"❌ Clear error: {e}")
    
    # Run sync
    try:
        sync_main()
        print("✅ Sync completed!")
    except Exception as e:
        print(f"❌ Sync error: {e}")
    
    # Check results
    check_database()
    
    print("\n🎯 NEXT: Test RJ62438 in webshop!")
