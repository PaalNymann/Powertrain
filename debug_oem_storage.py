#!/usr/bin/env python3
"""
Debug OEM storage format in database
"""

import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def debug_oem_storage():
    """Debug how OEM numbers are actually stored in the database"""
    
    print("🔍 DEBUGGING OEM STORAGE FORMAT")
    print("=" * 50)
    
    # Connect to database
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL not found in environment")
        return
    
    engine = create_engine(database_url)
    
    try:
        with engine.connect() as conn:
            print("✅ Connected to Railway database")
            
            # Check if we have the known OEM A2044102401
            known_oem = "A2044102401"
            print(f"\n🔍 Searching for known OEM: {known_oem}")
            
            # Try different search patterns
            search_patterns = [
                f"SELECT id, handle, title, original_nummer FROM shopify_products WHERE original_nummer LIKE '%{known_oem}%' LIMIT 5",
                f"SELECT id, handle, title, original_nummer FROM shopify_products WHERE original_nummer = '{known_oem}' LIMIT 5",
                f"SELECT id, handle, title, original_nummer FROM shopify_products WHERE UPPER(original_nummer) LIKE '%{known_oem.upper()}%' LIMIT 5",
                f"SELECT id, handle, title, original_nummer FROM shopify_products WHERE original_nummer::text LIKE '%{known_oem}%' LIMIT 5"
            ]
            
            for i, pattern in enumerate(search_patterns, 1):
                print(f"\n📋 Pattern {i}: {pattern}")
                try:
                    result = conn.execute(text(pattern))
                    rows = result.fetchall()
                    
                    if rows:
                        print(f"✅ Found {len(rows)} products:")
                        for row in rows:
                            print(f"   ID: {row[0]}")
                            print(f"   Handle: {row[1]}")
                            print(f"   Title: {row[2]}")
                            print(f"   Original_nummer: {repr(row[3])}")
                            print(f"   Type: {type(row[3])}")
                            print()
                    else:
                        print(f"❌ No products found with this pattern")
                        
                except Exception as e:
                    print(f"❌ Query failed: {e}")
            
            # Check a few random products to see OEM format
            print(f"\n🔍 Checking random products to see OEM format:")
            try:
                result = conn.execute(text("SELECT id, handle, title, original_nummer FROM shopify_products WHERE original_nummer IS NOT NULL AND original_nummer != '' LIMIT 10"))
                rows = result.fetchall()
                
                if rows:
                    print(f"✅ Found {len(rows)} products with OEM data:")
                    for row in rows:
                        print(f"   Handle: {row[1]}")
                        print(f"   Original_nummer: {repr(row[3])}")
                        print(f"   Type: {type(row[3])}")
                        print()
                else:
                    print(f"❌ No products found with OEM data")
                    
            except Exception as e:
                print(f"❌ Random query failed: {e}")
                
            # Check if MA01002 exists (the product we know should match)
            print(f"\n🔍 Searching for product MA01002:")
            try:
                result = conn.execute(text("SELECT id, handle, title, original_nummer FROM shopify_products WHERE handle LIKE '%ma01002%' OR title LIKE '%MA01002%' OR id LIKE '%MA01002%' LIMIT 5"))
                rows = result.fetchall()
                
                if rows:
                    print(f"✅ Found MA01002 products:")
                    for row in rows:
                        print(f"   ID: {row[0]}")
                        print(f"   Handle: {row[1]}")
                        print(f"   Title: {row[2]}")
                        print(f"   Original_nummer: {repr(row[3])}")
                        print()
                else:
                    print(f"❌ MA01002 not found in database")
                    
            except Exception as e:
                print(f"❌ MA01002 query failed: {e}")
    
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_oem_storage()
