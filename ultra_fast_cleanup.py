#!/usr/bin/env python3
"""
Ultra-fast cleanup script - Delete products with concurrent requests
"""

import os
import requests
import time
import concurrent.futures
from dotenv import load_dotenv

load_dotenv()

# Configuration
SHOP_DOMAIN = os.getenv("SHOPIFY_DOMAIN")
SHOP_TOKEN = os.getenv("SHOPIFY_TOKEN")

HEADERS = {
    "X-Shopify-Access-Token": SHOP_TOKEN,
    "Content-Type": "application/json"
}

def delete_product(product_id):
    """Delete a single product"""
    try:
        delete_url = f"https://{SHOP_DOMAIN}/admin/api/2023-10/products/{product_id}.json"
        response = requests.delete(delete_url, headers=HEADERS, timeout=5)
        return response.status_code == 200
    except:
        return False

def ultra_fast_cleanup():
    """Delete products with concurrent requests"""
    print("🚀 ULTRA-FAST CLEANUP - DELETE ALL PRODUCTS")
    print("=" * 55)
    
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
    
    # Get all product IDs first
    print("📥 Fetching all product IDs...")
    all_product_ids = []
    page_info = None
    
    while True:
        url = f"https://{SHOP_DOMAIN}/admin/api/2023-10/products.json?limit=250&fields=id"
        if page_info:
            url += f"&page_info={page_info}"
        
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        products = data["products"]
        
        for product in products:
            all_product_ids.append(product["id"])
        
        print(f"   Fetched {len(products)} IDs (total: {len(all_product_ids)})")
        
        # Check for pagination
        link = response.headers.get("link", "")
        if 'rel="next"' in link:
            page_info = link.split("page_info=")[1].split(">")[0]
        else:
            break
    
    print(f"🚀 Starting concurrent deletion of {len(all_product_ids)} products...")
    
    # Delete with concurrent requests (10 workers)
    deleted_count = 0
    failed_count = 0
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        # Submit all delete tasks
        future_to_id = {executor.submit(delete_product, pid): pid for pid in all_product_ids}
        
        # Process completed tasks
        for i, future in enumerate(concurrent.futures.as_completed(future_to_id), 1):
            product_id = future_to_id[future]
            try:
                success = future.result()
                if success:
                    deleted_count += 1
                else:
                    failed_count += 1
                
                # Progress update every 100 products
                if i % 100 == 0:
                    print(f"   Progress: {i}/{len(all_product_ids)} products processed")
                    
            except Exception as e:
                failed_count += 1
    
    # Final verification
    count_response = requests.get(count_url, headers=HEADERS, timeout=30)
    final_count = count_response.json()["count"]
    
    print(f"\n🎉 ULTRA-FAST CLEANUP COMPLETE!")
    print(f"   📊 Products deleted: {deleted_count}")
    print(f"   ❌ Failed deletions: {failed_count}")
    print(f"   📊 Remaining products: {final_count}")
    
    if final_count == 0:
        print("   ✅ All products successfully deleted!")
        print("\n🚀 Ready for fresh sync with ~2,910 valid products from Rackbeat!")
    else:
        print(f"   ⚠️  {final_count} products still remain.")

if __name__ == "__main__":
    ultra_fast_cleanup() 