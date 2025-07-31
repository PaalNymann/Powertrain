#!/usr/bin/env python3
"""
Nuclear cleanup script - Delete ALL products from Shopify and start fresh
"""

import os
import requests
import time
from dotenv import load_dotenv

load_dotenv()

# Configuration
SHOP_DOMAIN = os.getenv("SHOPIFY_DOMAIN")
SHOP_TOKEN = os.getenv("SHOPIFY_TOKEN")

HEADERS = {
    "X-Shopify-Access-Token": SHOP_TOKEN,
    "Content-Type": "application/json"
}

def get_all_product_ids():
    """Get all product IDs from Shopify"""
    all_ids = []
    page_info = None
    
    print("📥 Fetching all product IDs from Shopify...")
    
    while True:
        url = f"https://{SHOP_DOMAIN}/admin/api/2023-10/products.json?limit=250&fields=id"
        if page_info:
            url += f"&page_info={page_info}"
        
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        products = data["products"]
        
        for product in products:
            all_ids.append(product["id"])
        
        print(f"   Fetched {len(products)} product IDs (total: {len(all_ids)})")
        
        # Check for pagination
        link = response.headers.get("link", "")
        if 'rel="next"' in link:
            page_info = link.split("page_info=")[1].split(">")[0]
        else:
            break
    
    return all_ids

def delete_product(product_id):
    """Delete a single product"""
    url = f"https://{SHOP_DOMAIN}/admin/api/2023-10/products/{product_id}.json"
    response = requests.delete(url, headers=HEADERS, timeout=30)
    return response.status_code == 200

def nuclear_cleanup():
    """Delete ALL products from Shopify"""
    print("☢️  NUCLEAR CLEANUP - DELETE ALL PRODUCTS")
    print("=" * 60)
    print("⚠️  WARNING: This will delete ALL products from Shopify!")
    print("⚠️  This action cannot be undone!")
    print()
    
    # Get confirmation
    response = input("Are you absolutely sure you want to delete ALL products? (type 'YES' to confirm): ")
    if response != "YES":
        print("❌ Cleanup cancelled.")
        return
    
    # Get all product IDs
    product_ids = get_all_product_ids()
    total_products = len(product_ids)
    
    print(f"\n🗑️  Found {total_products} products to delete")
    
    # Get final confirmation
    response = input(f"Delete all {total_products} products? (type 'DELETE' to confirm): ")
    if response != "DELETE":
        print("❌ Cleanup cancelled.")
        return
    
    # Delete all products
    print(f"\n🗑️  Deleting {total_products} products...")
    deleted_count = 0
    failed_count = 0
    
    for i, product_id in enumerate(product_ids, 1):
        if delete_product(product_id):
            deleted_count += 1
            if i % 100 == 0:  # Progress update every 100 products
                print(f"   Progress: {i}/{total_products} products deleted")
        else:
            failed_count += 1
            print(f"   ❌ Failed to delete product {product_id}")
        
        # Small delay to avoid rate limiting
        if i % 10 == 0:
            time.sleep(0.1)
    
    print(f"\n🎉 NUCLEAR CLEANUP COMPLETE!")
    print(f"   ✅ Successfully deleted: {deleted_count} products")
    print(f"   ❌ Failed to delete: {failed_count} products")
    print(f"   📊 Total processed: {total_products} products")
    
    # Verify cleanup
    print(f"\n🔍 Verifying cleanup...")
    count_url = f"https://{SHOP_DOMAIN}/admin/api/2023-10/products/count.json"
    count_response = requests.get(count_url, headers=HEADERS, timeout=30)
    remaining_count = count_response.json()["count"]
    
    print(f"   📊 Remaining products: {remaining_count}")
    
    if remaining_count == 0:
        print("   ✅ Cleanup successful! All products deleted.")
        print("\n🚀 Ready for fresh sync with ~2,910 valid products from Rackbeat!")
    else:
        print(f"   ⚠️  {remaining_count} products still remain.")

if __name__ == "__main__":
    nuclear_cleanup() 