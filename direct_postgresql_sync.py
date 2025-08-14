#!/usr/bin/env python3
"""
Direct PostgreSQL Railway Database Sync
Bypasses database.py module and connects directly to Railway PostgreSQL
Only includes Drivaksel and Mellomaksel products with stock and price
"""

import os
import sys
import requests
import re
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# Get Railway PostgreSQL connection string
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL or not DATABASE_URL.startswith('postgresql://'):
    sys.exit(f"❌ Invalid DATABASE_URL: {DATABASE_URL}")

print(f"✅ Using Railway PostgreSQL: {DATABASE_URL[:50]}...")

# Rackbeat API configuration
RACKBEAT_API = os.getenv("RACKBEAT_ENDPOINT", "https://app.rackbeat.com/api/products")
RACKBEAT_KEY = os.getenv("RACKBEAT_API_KEY")

if not RACKBEAT_KEY:
    sys.exit("❌ Missing RACKBEAT_API_KEY in environment")

HEADERS = {
    "Authorization": f"Bearer {RACKBEAT_KEY}",
    "Content-Type": "application/json"
}

def fetch_all_rackbeat_products():
    """Fetch all products from Rackbeat API"""
    print("📥 Fetching all Rackbeat products...")
    all_products = []
    page = 1
    
    while True:
        url = f"{RACKBEAT_API}?page={page}&limit=250"
        response = requests.get(url, headers=HEADERS, timeout=30)
        
        if response.status_code not in [200, 206]:
            print(f"❌ Error fetching page {page}: {response.status_code}")
            break
            
        data = response.json()
        products = data.get("products", [])
        
        if not products:
            break
            
        print(f"📦 Page {page}: {len(products)} products")
        all_products.extend(products)
        
        # Check if we have more pages
        if page >= data.get("pages", 1):
            break
            
        page += 1
    
    print(f"✅ Total products fetched: {len(all_products)}")
    return all_products

def filter_products(products):
    """Filter products to only include Drivaksel and Mellomaksel with stock and price"""
    print("🔍 Filtering products...")
    filtered = []
    
    for product in products:
        # Check stock and price
        if not (product.get("available_quantity", 0) >= 1 and product.get("sales_price", 0) > 0):
            continue
            
        # Check product group
        group_name = product.get("group", {}).get("name", "")
        if group_name not in ["Drivaksel", "Mellomaksel"]:
            continue
            
        filtered.append(product)
        print(f"✅ {product.get('name', 'N/A')[:40]} - Group: {group_name}")
    
    print(f"📊 Filtered products: {len(filtered)}")
    return filtered

def extract_oem_numbers(description):
    """Extract OEM numbers from product description using regex"""
    if not description:
        return ""
        
    oem_numbers = []
    patterns = [
        r'\b\d{6,10}\b',           # 6-10 digit numbers like 8252034
        r'\b[A-Z]{2,4}\d{3,8}\b',  # Patterns like BMW123456
        r'\b[A-Z0-9]{6,12}\b',     # Alphanumeric codes
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, description)
        oem_numbers.extend(matches)
    
    # Remove duplicates and join with commas
    unique_oems = list(set(oem_numbers))
    return ", ".join(unique_oems)

def sync_to_railway_postgresql(products):
    """Sync filtered products directly to Railway PostgreSQL database"""
    print("🔄 Syncing to Railway PostgreSQL...")
    
    try:
        # Connect directly to PostgreSQL
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Clear existing products (fresh sync)
        print("🗑️ Clearing existing products...")
        cursor.execute("DELETE FROM product_metafields")
        cursor.execute("DELETE FROM shopify_products")
        conn.commit()
        
        synced_count = 0
        for i, product in enumerate(products):
            try:
                print(f"📦 Processing {i+1}/{len(products)}: {product.get('name', 'N/A')[:40]}")
                
                # Insert into shopify_products
                product_id = product.get("number", f"rb_{i}")
                cursor.execute("""
                    INSERT INTO shopify_products 
                    (id, title, handle, sku, price, inventory_quantity, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    product_id,
                    product.get("name", ""),
                    product.get("number", "").lower().replace(" ", "-"),
                    product.get("number", ""),
                    float(product.get("sales_price", 0)),
                    int(product.get("available_quantity", 0)),
                    datetime.now(),
                    datetime.now()
                ))
                
                # Extract OEM numbers from original_nummer field (not description)
                # Check if Rackbeat has original_nummer field directly
                oem_string = ""
                if "original_nummer" in product:
                    oem_string = str(product["original_nummer"])
                else:
                    # Fallback: extract from description if original_nummer field doesn't exist
                    description = product.get("description", "")
                    oem_string = extract_oem_numbers(description)
                
                print(f"   🔍 OEM extracted: {oem_string[:50]}..." if len(oem_string) > 50 else f"   🔍 OEM extracted: {oem_string}")
                
                # Insert metafields
                metafields_data = {
                    "number": product.get("number", ""),
                    "original_nummer": oem_string,
                    "product_group": product.get("group", {}).get("name", ""),
                    "i_nettbutikk": "ja",
                    "available_quantity": str(product.get("available_quantity", 0)),
                    "sales_price": str(product.get("sales_price", 0))
                }
                
                for key, value in metafields_data.items():
                    cursor.execute("""
                        INSERT INTO product_metafields 
                        (id, product_id, namespace, key, value, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (
                        f"{product_id}_{key}",
                        product_id,
                        "custom",
                        key,
                        str(value),
                        datetime.now()
                    ))
                
                synced_count += 1
                
                # Commit every 50 products
                if synced_count % 50 == 0:
                    conn.commit()
                    print(f"💾 Committed {synced_count} products...")
                    
            except Exception as e:
                print(f"⚠️ Error processing product {product.get('number', 'N/A')}: {e}")
                conn.rollback()
                continue
        
        # Final commit
        conn.commit()
        print(f"✅ Successfully synced {synced_count} products to Railway PostgreSQL!")
        
        # Verify sync
        cursor.execute("SELECT COUNT(*) FROM shopify_products")
        product_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM product_metafields")
        metafield_count = cursor.fetchone()[0]
        
        print(f"📊 Verification - Products: {product_count}, Metafields: {metafield_count}")
        
        return synced_count
        
    except Exception as e:
        print(f"❌ PostgreSQL sync error: {e}")
        raise
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

def main():
    print("🚀 Starting direct Railway PostgreSQL sync...")
    print("=" * 60)
    
    try:
        # Fetch all Rackbeat products
        all_products = fetch_all_rackbeat_products()
        
        # Filter to only Drivaksel and Mellomaksel with stock and price
        filtered_products = filter_products(all_products)
        
        if not filtered_products:
            print("❌ No products passed filtering criteria")
            return
        
        # Sync to Railway PostgreSQL
        synced_count = sync_to_railway_postgresql(filtered_products)
        
        print("\n🎉 Direct Railway PostgreSQL sync completed successfully!")
        print(f"📊 Total products synced: {synced_count}")
        
    except Exception as e:
        print(f"❌ Sync failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
