#!/usr/bin/env python3
"""
Direct Railway Database Sync
Syncs filtered Rackbeat products directly to Railway PostgreSQL database
Only includes Drivaksel and Mellomaksel products with stock and price
"""

import os
import sys
import requests
import re
from dotenv import load_dotenv
from database import SessionLocal, ShopifyProduct, ProductMetafield
from datetime import datetime

# Load environment variables from .env file
load_dotenv()

# Ensure DATABASE_URL is loaded correctly
db_url = os.getenv('DATABASE_URL')
print(f"🔧 DATABASE_URL loaded: {db_url[:50] if db_url else 'Not found'}...")

if not db_url:
    sys.exit("❌ DATABASE_URL not found in environment. Cannot proceed without database connection.")

if not db_url.startswith('postgresql://'):
    sys.exit(f"❌ Expected PostgreSQL DATABASE_URL, got: {db_url[:50]}...")

print("✅ Using Railway PostgreSQL database")

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
    """Filter products to only include Drivaksel and Mellomaksel with stock, price, and i_nettbutikk = ja"""
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
            
        # Check i_nettbutikk = 'ja' (webshop availability)
        i_nettbutikk = product.get("i_nettbutikk", "").lower()
        if i_nettbutikk != "ja":
            continue
            
        filtered.append(product)
        print(f"✅ {product.get('name', 'N/A')[:40]} - Group: {group_name} - Webshop: {i_nettbutikk}")
    
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

def sync_to_railway_database(products):
    """Sync filtered products to Railway PostgreSQL database"""
    print("🔄 Syncing to Railway database...")
    
    session = SessionLocal()
    try:
        # Clear existing products (we'll do a fresh sync)
        print("🗑️ Clearing existing products...")
        session.query(ProductMetafield).delete()
        session.query(ShopifyProduct).delete()
        session.commit()
        
        synced_count = 0
        for i, product in enumerate(products):
            try:
                print(f"📦 Processing {i+1}/{len(products)}: {product.get('name', 'N/A')[:40]}")
                
                # Determine Shopify category based on Rackbeat group
                group_name = product.get("group", {}).get("name", "")
                shopify_category = group_name if group_name in ["Drivaksel", "Mellomaksel"] else "Uncategorized"
                
                # Create ShopifyProduct record
                shopify_product = ShopifyProduct(
                    id=product.get("number", f"rb_{i}"),  # Use Rackbeat number as ID
                    title=product.get("name", ""),
                    handle=product.get("number", "").lower().replace(" ", "-"),
                    sku=product.get("number", ""),
                    price=float(product.get("sales_price", 0)),
                    inventory_quantity=int(product.get("available_quantity", 0)),
                    product_type=shopify_category,  # Set Shopify category
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                
                session.add(shopify_product)
                session.flush()  # Get the ID
                
                # Extract OEM numbers from description
                description = product.get("description", "")
                oem_string = extract_oem_numbers(description)
                
                # Create metafields
                metafields_data = {
                    "number": product.get("number", ""),
                    "original_nummer": oem_string,
                    "product_group": product.get("group", {}).get("name", ""),
                    "i_nettbutikk": "ja",
                    "available_quantity": str(product.get("available_quantity", 0)),
                    "sales_price": str(product.get("sales_price", 0))
                }
                
                for key, value in metafields_data.items():
                    metafield = ProductMetafield(
                        id=f"{shopify_product.id}_{key}",
                        product_id=shopify_product.id,
                        namespace="custom",
                        key=key,
                        value=str(value),
                        created_at=datetime.now()
                    )
                    session.add(metafield)
                
                synced_count += 1
                
                # Commit every 50 products to avoid memory issues
                if synced_count % 50 == 0:
                    session.commit()
                    print(f"💾 Committed {synced_count} products...")
                    
            except Exception as e:
                print(f"⚠️ Error processing product {product.get('number', 'N/A')}: {e}")
                session.rollback()
                continue
        
        # Final commit
        session.commit()
        print(f"✅ Successfully synced {synced_count} products to Railway database!")
        
    except Exception as e:
        print(f"❌ Database sync error: {e}")
        session.rollback()
        raise
    finally:
        session.close()

def main():
    print("🚀 Starting direct Railway database sync...")
    print("=" * 60)
    
    try:
        # Fetch all Rackbeat products
        all_products = fetch_all_rackbeat_products()
        
        # Filter to only Drivaksel and Mellomaksel with stock and price
        filtered_products = filter_products(all_products)
        
        if not filtered_products:
            print("❌ No products passed filtering criteria")
            return
        
        # Sync to Railway database
        sync_to_railway_database(filtered_products)
        
        print("\n🎉 Direct Railway sync completed successfully!")
        print(f"📊 Total products synced: {len(filtered_products)}")
        
    except Exception as e:
        print(f"❌ Sync failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
