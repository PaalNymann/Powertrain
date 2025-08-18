#!/usr/bin/env python3
"""
PostgreSQL Shopify Cleanup Script
Remove all products EXCEPT those that are in Railway PostgreSQL database
"""

import os
import requests
import json
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SHOPIFY_DOMAIN = os.getenv('SHOPIFY_DOMAIN')
SHOPIFY_TOKEN = os.getenv('SHOPIFY_TOKEN')
DATABASE_URL = 'postgresql://postgres:pmTNRdLNPAwZTYvtBFsqvfmjUOoNEuqM@shinkansen.proxy.rlwy.net:13074/railway'

def get_shopify_headers():
    return {
        'X-Shopify-Access-Token': SHOPIFY_TOKEN,
        'Content-Type': 'application/json'
    }

def get_eligible_product_ids_from_db():
    """Get list of product IDs that should remain in Shopify (from Railway PostgreSQL)"""
    try:
        print("🔗 Connecting to Railway PostgreSQL...")
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # Get all products that are in our Railway database (these are the eligible ones)
        cursor.execute("SELECT DISTINCT id FROM shopify_products")
        eligible_ids = [row[0] for row in cursor.fetchall()]
        
        cursor.close()
        conn.close()
        
        print(f"✅ Found {len(eligible_ids)} eligible products in Railway PostgreSQL")
        return set(eligible_ids)
    except Exception as e:
        print(f"❌ Database error: {e}")
        return set()

def get_shopify_product_count():
    """Get total count of products in Shopify"""
    url = f"https://{SHOPIFY_DOMAIN}/admin/api/2023-10/products/count.json"
    headers = get_shopify_headers()
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get('count', 0)
    return 0

def get_shopify_products_batch(limit=250, since_id=None):
    """Get a batch of products from Shopify"""
    url = f"https://{SHOPIFY_DOMAIN}/admin/api/2023-10/products.json"
    headers = get_shopify_headers()
    
    params = {'limit': limit, 'fields': 'id,title'}
    if since_id:
        params['since_id'] = since_id
    
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json().get('products', [])
    return []

def delete_shopify_product(product_id):
    """Delete a product from Shopify"""
    url = f"https://{SHOPIFY_DOMAIN}/admin/api/2023-10/products/{product_id}.json"
    headers = get_shopify_headers()
    
    response = requests.delete(url, headers=headers)
    if response.status_code == 200:
        return True
    else:
        print(f"❌ Failed to delete product {product_id}: {response.status_code}")
        return False

def main():
    print("🚀 Starting PostgreSQL Shopify Cleanup...")
    
    # Step 1: Get eligible products from Railway PostgreSQL
    print("\n📊 STEP 1: Getting eligible products from Railway PostgreSQL...")
    eligible_ids = get_eligible_product_ids_from_db()
    
    if not eligible_ids:
        print("❌ No eligible products found in PostgreSQL database! Aborting cleanup.")
        return
    
    # Step 2: Get total Shopify product count
    print("\n📊 STEP 2: Checking Shopify product count...")
    total_shopify_products = get_shopify_product_count()
    print(f"Total products in Shopify: {total_shopify_products}")
    
    # Step 3: Process products in batches
    print(f"\n🔄 STEP 3: Processing products in batches...")
    
    processed = 0
    deleted = 0
    kept = 0
    since_id = None
    
    while True:
        # Get batch of products
        products = get_shopify_products_batch(limit=250, since_id=since_id)
        
        if not products:
            break
        
        print(f"Processing batch of {len(products)} products...")
        
        for product in products:
            product_id = str(product['id'])
            processed += 1
            
            if product_id in eligible_ids:
                print(f"✅ Keeping: {product_id} - {product['title'][:50]}")
                kept += 1
            else:
                print(f"🗑️  Deleting: {product_id} - {product['title'][:50]}")
                if delete_shopify_product(product_id):
                    deleted += 1
                else:
                    print(f"❌ Failed to delete {product_id}")
        
        # Update since_id for next batch
        since_id = products[-1]['id']
        
        print(f"Progress: {processed}/{total_shopify_products} processed, {deleted} deleted, {kept} kept")
        
        # Continue until all products are processed
    
    print(f"\n📊 CLEANUP RESULTS:")
    print(f"  Total processed: {processed}")
    print(f"  Products deleted: {deleted}")
    print(f"  Products kept: {kept}")
    print(f"  Remaining in Shopify: ~{total_shopify_products - deleted}")
    
    if deleted > 0:
        print(f"\n✅ Successfully cleaned up {deleted} products!")
        print(f"Run script again to continue cleanup of remaining products.")
    else:
        print(f"\n⚠️  No products were deleted. Check API permissions or product eligibility.")

if __name__ == "__main__":
    main()
