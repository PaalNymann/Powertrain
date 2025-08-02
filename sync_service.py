#!/usr/bin/env python3
"""
Full Rackbeat → Shopify synchroniser
• Paginates through ALL Rackbeat pages
• Filters to products that have stock & price
• Creates/updates products in Shopify
• Writes/updates required metafields
• Unpublishes (draft) any Shopify product not in the filtered list
"""

import requests
import os
import time
from datetime import datetime
from dotenv import load_dotenv
from database import update_shopify_cache, get_cache_stats

# Load environment variables
load_dotenv()

# API Configuration
SHOPIFY_DOMAIN = os.getenv('SHOPIFY_DOMAIN')
SHOPIFY_TOKEN = os.getenv('SHOPIFY_TOKEN')
SHOPIFY_VERSION = os.getenv('SHOPIFY_VERSION', '2023-10')

def fetch_products_batch(page, limit=100):
    """Fetch a single batch of products"""
    try:
        shopify_url = f"https://{SHOPIFY_DOMAIN}/admin/api/{SHOPIFY_VERSION}/products.json?limit={limit}&page={page}"
        headers = {
            "X-Shopify-Access-Token": SHOPIFY_TOKEN,
            "Content-Type": "application/json"
        }
        
        print(f"📥 Fetching batch {page} with {limit} products...")
        res = requests.get(shopify_url, headers=headers, timeout=30)
        
        if res.status_code != 200:
            print(f"❌ Error on batch {page}: {res.status_code}")
            return []
        
        data = res.json().get("products", [])
        print(f"📦 Found {len(data)} products in batch {page}")
        
        # Add metafields for each product
        for i, product in enumerate(data):
            product_id = product["id"]
            metafields_url = f"https://{SHOPIFY_DOMAIN}/admin/api/{SHOPIFY_VERSION}/products/{product_id}/metafields.json"
            meta_res = requests.get(metafields_url, headers=headers, timeout=10)
            
            if meta_res.status_code == 200:
                product['metafields'] = meta_res.json().get("metafields", [])
            else:
                product['metafields'] = []
            
            # Progress indicator
            if (i + 1) % 20 == 0:
                print(f"   📋 Processed {i + 1}/{len(data)} products in batch {page}")
        
        return data
        
    except Exception as e:
        print(f"❌ Error fetching batch {page}: {e}")
        return []

def sync_all_products():
    """Sync all products in batches"""
    print(f"🚀 Starting full product sync at {datetime.now()}")
    
    all_products = []
    page = 1
    max_pages = 50  # Safety limit
    
    while page <= max_pages:
        print(f"\n--- Processing page {page} ---")
        
        # Fetch batch
        batch = fetch_products_batch(page, limit=100)
        
        if not batch:
            print(f"✅ No more products found on page {page}")
            break
        
        all_products.extend(batch)
        print(f"📊 Total products so far: {len(all_products)}")
        
        # Update database with current batch
        try:
            success = update_shopify_cache(all_products)
            if success:
                stats = get_cache_stats()
                print(f"✅ Database updated: {stats['products']} products, {stats['metafields']} metafields")
            else:
                print("❌ Failed to update database")
        except Exception as e:
            print(f"❌ Error updating database: {e}")
        
        page += 1
        
        # Wait between batches to avoid rate limiting
        if page <= max_pages:
            print("⏳ Waiting 5 seconds before next batch...")
            time.sleep(5)
    
    print(f"\n🎉 Sync completed! Total products: {len(all_products)}")
    return len(all_products)

def sync_incremental():
    """Sync only new products (incremental update)"""
    print(f"🔄 Starting incremental sync at {datetime.now()}")
    
    # Get current stats
    current_stats = get_cache_stats()
    current_count = current_stats['products']
    
    print(f"📊 Current database has {current_count} products")
    
    # Fetch latest batch to check for new products
    latest_batch = fetch_products_batch(1, limit=100)
    
    if latest_batch:
        # Check if we have new products
        if len(latest_batch) > 0:
            print(f"🆕 Found {len(latest_batch)} potential new products")
            
            # For now, just update with latest batch
            try:
                success = update_shopify_cache(latest_batch)
                if success:
                    new_stats = get_cache_stats()
                    print(f"✅ Updated: {new_stats['products']} products, {new_stats['metafields']} metafields")
                else:
                    print("❌ Failed to update")
            except Exception as e:
                print(f"❌ Error updating: {e}")
        else:
            print("✅ No new products found")
    else:
        print("❌ Failed to fetch latest batch")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "full":
            sync_all_products()
        elif sys.argv[1] == "incremental":
            sync_incremental()
        else:
            print("Usage: python sync_service.py [full|incremental]")
    else:
        print("Usage: python sync_service.py [full|incremental]")
        print("  full: Sync all products")
        print("  incremental: Sync only new products") 