#!/usr/bin/env python3
"""
Admin cleanup - Try different Shopify Admin API methods
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

SHOP_DOMAIN = os.getenv("SHOPIFY_DOMAIN")
SHOP_TOKEN = os.getenv("SHOPIFY_TOKEN")

HEADERS = {
    "X-Shopify-Access-Token": SHOP_TOKEN,
    "Content-Type": "application/json"
}

def admin_cleanup():
    print("🔧 ADMIN CLEANUP - ALTERNATIVE METHODS")
    print("=" * 40)
    
    # Method 1: Try to use the Shopify Admin API to set all products to draft
    print("📝 Method 1: Setting all products to draft...")
    
    # Get all product IDs first
    all_ids = []
    page_info = None
    
    while True:
        url = f"https://{SHOP_DOMAIN}/admin/api/2023-10/products.json?limit=250&fields=id"
        if page_info:
            url += f"&page_info={page_info}"
        
        response = requests.get(url, headers=HEADERS, timeout=30)
        if response.status_code != 200:
            break
            
        data = response.json()
        products = data["products"]
        
        if not products:
            break
            
        for product in products:
            all_ids.append(product["id"])
        
        print(f"   Collected {len(all_ids)} product IDs...")
        
        # Check for pagination
        link = response.headers.get("link", "")
        if 'rel="next"' in link:
            page_info = link.split("page_info=")[1].split(">")[0]
        else:
            break
    
    print(f"📊 Total products found: {len(all_ids)}")
    
    if len(all_ids) == 0:
        print("✅ No products to process!")
        return
    
    # Method 2: Try to delete products in larger batches
    print("\n🗑️ Method 2: Deleting products in larger batches...")
    
    # Delete in batches of 250 (maximum allowed)
    batch_size = 250
    deleted_total = 0
    
    for i in range(0, len(all_ids), batch_size):
        batch = all_ids[i:i + batch_size]
        print(f"   Deleting batch {i//batch_size + 1}: {len(batch)} products...")
        
        # Delete each product in the batch
        batch_deleted = 0
        for product_id in batch:
            delete_url = f"https://{SHOP_DOMAIN}/admin/api/2023-10/products/{product_id}.json"
            delete_response = requests.delete(delete_url, headers=HEADERS, timeout=10)
            
            if delete_response.status_code == 200:
                batch_deleted += 1
        
        deleted_total += batch_deleted
        print(f"   ✅ Deleted {batch_deleted}/{len(batch)} (total: {deleted_total})")
    
    # Final check
    count_url = f"https://{SHOP_DOMAIN}/admin/api/2023-10/products/count.json"
    count_response = requests.get(count_url, headers=HEADERS, timeout=30)
    final_count = count_response.json()["count"]
    
    print(f"\n🎉 ADMIN CLEANUP COMPLETE!")
    print(f"   📊 Products deleted: {deleted_total}")
    print(f"   📊 Remaining products: {final_count}")
    
    if final_count == 0:
        print("   ✅ All products successfully deleted!")
    else:
        print(f"   ⚠️  {final_count} products still remain.")

if __name__ == "__main__":
    admin_cleanup() 