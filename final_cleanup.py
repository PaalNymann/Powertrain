#!/usr/bin/env python3
"""
Final cleanup - Delete ALL products including drafts
"""

import os
import requests
import time
from dotenv import load_dotenv

load_dotenv()

SHOP_DOMAIN = os.getenv("SHOPIFY_DOMAIN")
SHOP_TOKEN = os.getenv("SHOPIFY_TOKEN")

HEADERS = {
    "X-Shopify-Access-Token": SHOP_TOKEN,
    "Content-Type": "application/json"
}

def final_cleanup():
    print("💥 FINAL CLEANUP - DELETE EVERYTHING")
    print("=" * 50)
    
    # Get current count (including drafts)
    count_url = f"https://{SHOP_DOMAIN}/admin/api/2023-10/products/count.json"
    count_response = requests.get(count_url, headers=HEADERS, timeout=30)
    current_count = count_response.json()["count"]
    
    print(f"📊 Total products in Shopify: {current_count}")
    
    if current_count == 0:
        print("✅ No products to delete!")
        return
    
    # Get confirmation
    response = input(f"DELETE ALL {current_count} products including drafts? (type 'DELETE ALL'): ")
    if response != "DELETE ALL":
        print("❌ Cancelled.")
        return
    
    print("💥 Starting final cleanup...")
    
    # Delete products in batches until none remain
    deleted_total = 0
    batch_count = 0
    
    while True:
        batch_count += 1
        
        # Get next batch of products (including drafts)
        url = f"https://{SHOP_DOMAIN}/admin/api/2023-10/products.json?limit=100&status=any"
        response = requests.get(url, headers=HEADERS, timeout=30)
        
        if response.status_code != 200:
            print(f"❌ Error: {response.status_code}")
            break
        
        products = response.json()["products"]
        
        if not products:
            print("✅ No more products to delete!")
            break
        
        print(f"🗑️  Batch {batch_count}: Deleting {len(products)} products...")
        
        # Delete each product in the batch
        batch_deleted = 0
        for product in products:
            product_id = product["id"]
            product_title = product.get("title", "Unknown")
            
            delete_url = f"https://{SHOP_DOMAIN}/admin/api/2023-10/products/{product_id}.json"
            delete_response = requests.delete(delete_url, headers=HEADERS, timeout=10)
            
            if delete_response.status_code == 200:
                batch_deleted += 1
            else:
                print(f"   ❌ Failed to delete: {product_title}")
        
        deleted_total += batch_deleted
        print(f"   ✅ Deleted {batch_deleted}/{len(products)} (total: {deleted_total})")
        
        # Small delay
        time.sleep(0.5)
    
    # Final verification
    count_response = requests.get(count_url, headers=HEADERS, timeout=30)
    final_count = count_response.json()["count"]
    
    print(f"\n🎉 FINAL CLEANUP COMPLETE!")
    print(f"   📊 Products deleted: {deleted_total}")
    print(f"   📊 Remaining products: {final_count}")
    
    if final_count == 0:
        print("   ✅ ALL products successfully deleted!")
        print("\n🚀 Ready for fresh sync with ~1,675 valid products from Rackbeat!")
    else:
        print(f"   ⚠️  {final_count} products still remain.")

if __name__ == "__main__":
    final_cleanup() 