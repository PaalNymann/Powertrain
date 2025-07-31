#!/usr/bin/env python3
"""
Simple curl cleanup - No jq required
"""

import os
import subprocess
import json
import time
from dotenv import load_dotenv

load_dotenv()

SHOP_DOMAIN = os.getenv("SHOPIFY_DOMAIN")
SHOP_TOKEN = os.getenv("SHOPIFY_TOKEN")

def simple_curl_cleanup():
    print("⚡ SIMPLE CURL CLEANUP")
    print("=" * 30)
    
    # Get current count
    count_cmd = f'curl -s "https://{SHOP_DOMAIN}/admin/api/2023-10/products/count.json" -H "X-Shopify-Access-Token: {SHOP_TOKEN}"'
    result = subprocess.run(count_cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode != 0:
        print("❌ Failed to get product count")
        return
    
    count_data = json.loads(result.stdout)
    current_count = count_data["count"]
    
    print(f"📊 Products to delete: {current_count}")
    
    if current_count == 0:
        print("✅ No products to delete!")
        return
    
    # Confirm
    response = input(f"Delete all {current_count} products? (type 'DELETE'): ")
    if response != "DELETE":
        print("❌ Cancelled.")
        return
    
    print("⚡ Starting deletion...")
    
    deleted_total = 0
    
    while True:
        # Get products
        get_cmd = f'curl -s "https://{SHOP_DOMAIN}/admin/api/2023-10/products.json?limit=100" -H "X-Shopify-Access-Token: {SHOP_TOKEN}"'
        result = subprocess.run(get_cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0:
            print("❌ Failed to get products")
            break
        
        try:
            data = json.loads(result.stdout)
            products = data.get("products", [])
        except:
            print("❌ Failed to parse products")
            break
        
        if not products:
            print("✅ No more products!")
            break
        
        print(f"🗑️  Deleting {len(products)} products...")
        
        # Delete each product
        batch_deleted = 0
        for product in products:
            product_id = product["id"]
            delete_cmd = f'curl -X DELETE "https://{SHOP_DOMAIN}/admin/api/2023-10/products/{product_id}.json" -H "X-Shopify-Access-Token: {SHOP_TOKEN}" -s'
            delete_result = subprocess.run(delete_cmd, shell=True, capture_output=True, text=True)
            
            if delete_result.returncode == 0:
                batch_deleted += 1
        
        deleted_total += batch_deleted
        print(f"   ✅ Deleted {batch_deleted}/{len(products)} (total: {deleted_total})")
        
        # Small delay
        time.sleep(0.1)
    
    # Final check
    result = subprocess.run(count_cmd, shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        final_count = json.loads(result.stdout)["count"]
        print(f"\n🎉 CLEANUP COMPLETE!")
        print(f"📊 Deleted: {deleted_total}")
        print(f"📊 Remaining: {final_count}")
        
        if final_count == 0:
            print("✅ All products deleted!")
        else:
            print(f"⚠️  {final_count} products still remain.")

if __name__ == "__main__":
    simple_curl_cleanup() 