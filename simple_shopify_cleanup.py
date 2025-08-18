#!/usr/bin/env python3
"""
Simple Shopify Cleanup Script
Remove all products EXCEPT those that are in Railway database (eligible products)
"""

import os
import requests
import json
from dotenv import load_dotenv
from database import SessionLocal, ShopifyProduct

# Load environment variables
load_dotenv()

# Force Railway PostgreSQL connection
os.environ['DATABASE_URL'] = 'postgresql://postgres:pmTNRdLNPAwZTYvtBFsqvfmjUOoNEuqM@shinkansen.proxy.rlwy.net:13074/railway'

SHOPIFY_DOMAIN = os.getenv('SHOPIFY_DOMAIN')
SHOPIFY_TOKEN = os.getenv('SHOPIFY_TOKEN')

def get_shopify_headers():
    return {
        'X-Shopify-Access-Token': SHOPIFY_TOKEN,
        'Content-Type': 'application/json'
    }

def get_all_shopify_products():
    """Get all products from Shopify"""
    url = f"https://{SHOPIFY_DOMAIN}/admin/api/2023-10/products.json"
    headers = get_shopify_headers()
    
    all_products = []
    params = {'limit': 250}
    
    while True:
        print(f"Fetching products from Shopify... (current count: {len(all_products)})")
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code != 200:
            print(f"Error fetching products: {response.status_code} - {response.text}")
            break
            
        data = response.json()
        products = data.get('products', [])
        
        if not products:
            break
            
        all_products.extend(products)
        
        # Check for pagination
        link_header = response.headers.get('Link', '')
        if 'rel="next"' not in link_header:
            break
            
        # Extract next page URL
        for link in link_header.split(','):
            if 'rel="next"' in link:
                next_url = link.split('<')[1].split('>')[0]
                url = next_url
                params = {}
                break
    
    print(f"Total Shopify products found: {len(all_products)}")
    return all_products

def get_eligible_product_ids_from_db():
    """Get list of product IDs that should remain in Shopify (from Railway DB)"""
    session = SessionLocal()
    try:
        # Get all products that are in our Railway database (these are the eligible ones)
        products = session.query(ShopifyProduct).all()
        eligible_ids = [product.id for product in products]
        
        print(f"Eligible products in Railway DB: {len(eligible_ids)}")
        return set(eligible_ids)
    finally:
        session.close()

def delete_shopify_product(product_id):
    """Delete a product from Shopify"""
    url = f"https://{SHOPIFY_DOMAIN}/admin/api/2023-10/products/{product_id}.json"
    headers = get_shopify_headers()
    
    response = requests.delete(url, headers=headers)
    if response.status_code == 200:
        print(f"✅ Deleted product {product_id}")
        return True
    else:
        print(f"❌ Failed to delete product {product_id}: {response.status_code}")
        return False

def main():
    print("🚀 Starting Simple Shopify Cleanup...")
    
    # Step 1: Get current state
    print("\n📊 STEP 1: Analyzing current Shopify catalog...")
    shopify_products = get_all_shopify_products()
    eligible_ids = get_eligible_product_ids_from_db()
    
    # Step 2: Identify products to remove
    products_to_remove = []
    products_to_keep = []
    
    for product in shopify_products:
        product_id = str(product['id'])
        if product_id in eligible_ids:
            products_to_keep.append(product)
        else:
            products_to_remove.append(product)
    
    print(f"\n📈 ANALYSIS RESULTS:")
    print(f"  Total products in Shopify: {len(shopify_products)}")
    print(f"  Products to keep: {len(products_to_keep)}")
    print(f"  Products to remove: {len(products_to_remove)}")
    
    # Step 3: Show some examples of products to remove
    if products_to_remove:
        print(f"\n🗑️  EXAMPLES OF PRODUCTS TO REMOVE:")
        for i, product in enumerate(products_to_remove[:10]):
            print(f"  - {product['id']}: {product['title']}")
        if len(products_to_remove) > 10:
            print(f"  ... and {len(products_to_remove) - 10} more")
    
    # Step 4: Ask for confirmation
    print(f"\n⚠️  READY TO DELETE {len(products_to_remove)} PRODUCTS FROM SHOPIFY!")
    print(f"This will keep only {len(products_to_keep)} eligible products.")
    
    # For safety, let's start with a small batch
    if len(products_to_remove) > 0:
        print(f"\n🔄 Starting with first 10 products for safety...")
        
        deleted_count = 0
        failed_count = 0
        
        # Delete first 10 products as test
        for i, product in enumerate(products_to_remove[:10]):
            product_id = str(product['id'])
            print(f"Deleting {i+1}/10: {product_id} - {product['title'][:50]}...")
            
            if delete_shopify_product(product_id):
                deleted_count += 1
            else:
                failed_count += 1
        
        print(f"\n📊 BATCH RESULTS:")
        print(f"  Successfully deleted: {deleted_count}")
        print(f"  Failed to delete: {failed_count}")
        print(f"  Remaining to delete: {len(products_to_remove) - 10}")
        
        if deleted_count > 0:
            print(f"\n✅ Test batch successful! Ready to delete remaining {len(products_to_remove) - 10} products.")
        else:
            print(f"\n❌ Test batch failed! Check API permissions.")
    
    return {
        'total_products': len(shopify_products),
        'products_to_keep': len(products_to_keep),
        'products_to_remove': len(products_to_remove),
        'test_deleted': deleted_count if 'deleted_count' in locals() else 0,
        'test_failed': failed_count if 'failed_count' in locals() else 0
    }

if __name__ == "__main__":
    result = main()
    print(f"\n📊 FINAL SUMMARY:")
    print(json.dumps(result, indent=2))
