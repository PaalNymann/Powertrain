#!/usr/bin/env python3
"""
Bulk cleanup using Shopify's bulk operations API
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

def bulk_cleanup():
    print("🔥 BULK CLEANUP - SHOPIFY BULK OPERATIONS")
    print("=" * 50)
    
    # Get current count
    count_url = f"https://{SHOP_DOMAIN}/admin/api/2023-10/products/count.json"
    count_response = requests.get(count_url, headers=HEADERS, timeout=30)
    current_count = count_response.json()["count"]
    
    print(f"📊 Products in Shopify: {current_count}")
    
    if current_count == 0:
        print("✅ No products to delete!")
        return
    
    # Get confirmation
    response = input(f"Delete all {current_count} products using bulk operations? (type 'BULK'): ")
    if response != "BULK":
        print("❌ Cancelled.")
        return
    
    print("🔥 Starting bulk deletion...")
    
    # Create a bulk operation to delete all products
    bulk_url = f"https://{SHOP_DOMAIN}/admin/api/2023-10/bulk_operations.json"
    
    # First, let's try to delete all products by setting them to draft status
    print("📝 Setting all products to draft status...")
    
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
    
    print(f"📊 Total products to process: {len(all_ids)}")
    
    # Now let's try a different approach - use the sync service to unpublish products
    print("🔄 Using sync service to unpublish products...")
    
    # Start the sync service and call the full sync endpoint
    # This should handle the cleanup properly
    
    print("🚀 Starting sync service for proper cleanup...")
    
    # Let's just run the sync service which should handle this properly
    import subprocess
    import sys
    
    print("🔄 Running sync service to clean up products...")
    
    # Run the sync service
    sync_process = subprocess.Popen([sys.executable, 'sync_service.py'], 
                                   stdout=subprocess.PIPE, 
                                   stderr=subprocess.PIPE)
    
    time.sleep(5)  # Give it time to start
    
    try:
        # Call the full sync endpoint
        sync_url = "http://127.0.0.1:8001/sync/full"
        print(f"🔄 Calling sync endpoint: {sync_url}")
        
        response = requests.post(sync_url, timeout=300)  # 5 minutes timeout
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Sync completed: {result}")
        else:
            print(f"❌ Sync failed: {response.status_code}")
            print(f"Response: {response.text[:200]}")
            
    except Exception as e:
        print(f"❌ Error during sync: {e}")
    finally:
        sync_process.terminate()
        sync_process.wait()
    
    # Final check
    count_response = requests.get(count_url, headers=HEADERS, timeout=30)
    final_count = count_response.json()["count"]
    
    print(f"\n🎉 BULK CLEANUP COMPLETE!")
    print(f"   📊 Remaining products: {final_count}")
    
    if final_count == 0:
        print("   ✅ All products successfully removed!")
    else:
        print(f"   ⚠️  {final_count} products still remain.")

if __name__ == "__main__":
    bulk_cleanup() 