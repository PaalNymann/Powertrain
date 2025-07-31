#!/usr/bin/env python3
"""
Delete ALL products fast - regardless of status
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

def delete_all_fast():
    print("🚀 DELETE ALL PRODUCTS FAST")
    print("=" * 30)
    
    # Get count
    count_url = f"https://{SHOP_DOMAIN}/admin/api/2023-10/products/count.json"
    count_response = requests.get(count_url, headers=HEADERS, timeout=30)
    current_count = count_response.json()["count"]
    
    print(f"📊 Total products: {current_count}")
    
    if current_count == 0:
        print("✅ No products to delete!")
        return
    
    # Confirm
    response = input(f"Delete ALL {current_count} products? (type 'DELETE ALL'): ")
    if response != "DELETE ALL":
        print("❌ Cancelled.")
        return
    
    deleted_count = 0
    batch_size = 250  # Larger batch size
    
    while True:
        # Get products (any status)
        url = f"https://{SHOP_DOMAIN}/admin/api/2023-10/products.json?limit={batch_size}"
        response = requests.get(url, headers=HEADERS, timeout=30)
        
        if response.status_code != 200:
            print(f"❌ Error: {response.status_code}")
            break
        
        data = response.json()
        products = data["products"]
        
        if not products:
            print("✅ No more products to delete!")
            break
        
        print(f"🗑️ Deleting {len(products)} products...")
        
        # Delete each product
        for i, product in enumerate(products):
            product_id = product["id"]
            delete_url = f"https://{SHOP_DOMAIN}/admin/api/2023-10/products/{product_id}.json"
            delete_response = requests.delete(delete_url, headers=HEADERS, timeout=5)
            
            if delete_response.status_code == 200:
                deleted_count += 1
                if deleted_count % 50 == 0:
                    print(f"   Deleted {deleted_count} so far...")
        
        print(f"✅ Deleted batch of {len(products)} (total: {deleted_count})")
        
        # Minimal delay
        time.sleep(0.1)
    
    # Final check
    count_response = requests.get(count_url, headers=HEADERS, timeout=30)
    final_count = count_response.json()["count"]
    
    print(f"\n🎉 DONE!")
    print(f"Deleted: {deleted_count}")
    print(f"Remaining: {final_count}")

if __name__ == "__main__":
    delete_all_fast() 