#!/usr/bin/env python3
"""
Simple cleanup script - Delete products in small batches
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

def simple_cleanup():
    """Delete products in small batches"""
    print("🧹 SIMPLE CLEANUP - DELETE ALL PRODUCTS")
    print("=" * 50)
    
    # Get current count
    count_url = f"https://{SHOP_DOMAIN}/admin/api/2023-10/products/count.json"
    count_response = requests.get(count_url, headers=HEADERS, timeout=30)
    current_count = count_response.json()["count"]
    
    print(f"📊 Current products in Shopify: {current_count}")
    
    if current_count == 0:
        print("✅ No products to delete!")
        return
    
    # Get confirmation
    response = input(f"Delete all {current_count} products? (type 'DELETE' to confirm): ")
    if response != "DELETE":
        print("❌ Cleanup cancelled.")
        return
    
    # Delete in batches of 50
    batch_size = 50
    deleted_total = 0
    
    while True:
        # Get next batch of products
        url = f"https://{SHOP_DOMAIN}/admin/api/2023-10/products.json?limit={batch_size}"
        response = requests.get(url, headers=HEADERS, timeout=30)
        
        if response.status_code != 200:
            print(f"❌ Error fetching products: {response.status_code}")
            break
        
        products = response.json()["products"]
        
        if not products:
            print("✅ No more products to delete!")
            break
        
        print(f"🗑️  Deleting batch of {len(products)} products...")
        
        # Delete each product in the batch
        for product in products:
            product_id = product["id"]
            delete_url = f"https://{SHOP_DOMAIN}/admin/api/2023-10/products/{product_id}.json"
            delete_response = requests.delete(delete_url, headers=HEADERS, timeout=30)
            
            if delete_response.status_code == 200:
                deleted_total += 1
            else:
                print(f"   ❌ Failed to delete product {product_id}")
        
        print(f"   ✅ Deleted {len(products)} products (total: {deleted_total})")
        
        # Small delay to avoid rate limiting
        time.sleep(1)
    
    # Final verification
    count_response = requests.get(count_url, headers=HEADERS, timeout=30)
    final_count = count_response.json()["count"]
    
    print(f"\n🎉 CLEANUP COMPLETE!")
    print(f"   📊 Products deleted: {deleted_total}")
    print(f"   📊 Remaining products: {final_count}")
    
    if final_count == 0:
        print("   ✅ All products successfully deleted!")
        print("\n🚀 Ready for fresh sync with ~2,910 valid products from Rackbeat!")
    else:
        print(f"   ⚠️  {final_count} products still remain.")

if __name__ == "__main__":
    simple_cleanup() 