#!/usr/bin/env python3
"""
Ultra-fast concurrent deletion
"""

import os
import requests
import time
import concurrent.futures
from dotenv import load_dotenv

load_dotenv()

SHOP_DOMAIN = os.getenv("SHOPIFY_DOMAIN")
SHOP_TOKEN = os.getenv("SHOPIFY_TOKEN")

HEADERS = {
    "X-Shopify-Access-Token": SHOP_TOKEN,
    "Content-Type": "application/json"
}

def delete_product(product_id):
    """Delete a single product"""
    delete_url = f"https://{SHOP_DOMAIN}/admin/api/2023-10/products/{product_id}.json"
    try:
        response = requests.delete(delete_url, headers=HEADERS, timeout=10)
        return response.status_code == 200
    except:
        return False

def ultra_fast_delete():
    print("⚡ ULTRA-FAST CONCURRENT DELETE")
    print("=" * 35)
    
    # Get count
    count_url = f"https://{SHOP_DOMAIN}/admin/api/2023-10/products/count.json"
    count_response = requests.get(count_url, headers=HEADERS, timeout=30)
    current_count = count_response.json()["count"]
    
    print(f"📊 Total products: {current_count}")
    
    if current_count == 0:
        print("✅ No products to delete!")
        return
    
    # Confirm
    response = input(f"Delete ALL {current_count} products with concurrent requests? (type 'CONCURRENT'): ")
    if response != "CONCURRENT":
        print("❌ Cancelled.")
        return
    
    deleted_count = 0
    batch_size = 100  # Get 100 at a time
    max_workers = 20  # 20 concurrent deletions
    
    start_time = time.time()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        while True:
            # Get products
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
            
            print(f"🗑️ Deleting {len(products)} products concurrently...")
            
            # Get product IDs
            product_ids = [product["id"] for product in products]
            
            # Submit all deletions concurrently
            futures = [executor.submit(delete_product, pid) for pid in product_ids]
            
            # Wait for all to complete and count successes
            batch_deleted = sum(1 for future in concurrent.futures.as_completed(futures) if future.result())
            deleted_count += batch_deleted
            
            elapsed = time.time() - start_time
            rate = deleted_count / elapsed if elapsed > 0 else 0
            
            print(f"✅ Deleted {batch_deleted}/{len(products)} in batch (total: {deleted_count}, rate: {rate:.1f}/sec)")
    
    total_time = time.time() - start_time
    
    # Final check
    count_response = requests.get(count_url, headers=HEADERS, timeout=30)
    final_count = count_response.json()["count"]
    
    print(f"\n🎉 DONE!")
    print(f"Deleted: {deleted_count}")
    print(f"Time: {total_time:.1f} seconds")
    print(f"Rate: {deleted_count/total_time:.1f} products/second")
    print(f"Remaining: {final_count}")

if __name__ == "__main__":
    ultra_fast_delete() 