#!/usr/bin/env python3
"""
Draft then delete - Set products to draft first, then delete
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

def draft_then_delete():
    print("📝 DRAFT THEN DELETE")
    print("=" * 25)
    
    # Get count
    count_url = f"https://{SHOP_DOMAIN}/admin/api/2023-10/products/count.json"
    count_response = requests.get(count_url, headers=HEADERS, timeout=30)
    current_count = count_response.json()["count"]
    
    print(f"Products: {current_count}")
    
    if current_count == 0:
        print("✅ Done!")
        return
    
    # Confirm
    response = input(f"Set all {current_count} products to draft, then delete? (type 'YES'): ")
    if response != "YES":
        print("❌ Cancelled.")
        return
    
    # Step 1: Set all products to draft
    print("📝 Step 1: Setting all products to draft...")
    
    draft_count = 0
    
    while True:
        # Get 100 products
        url = f"https://{SHOP_DOMAIN}/admin/api/2023-10/products.json?limit=100"
        response = requests.get(url, headers=HEADERS, timeout=30)
        
        if response.status_code != 200:
            print(f"❌ Error: {response.status_code}")
            break
        
        data = response.json()
        products = data["products"]
        
        if not products:
            print("✅ No more products to draft!")
            break
        
        print(f"Setting {len(products)} products to draft...")
        
        # Set each to draft
        for product in products:
            product_id = product["id"]
            update_url = f"https://{SHOP_DOMAIN}/admin/api/2023-10/products/{product_id}.json"
            update_data = {"product": {"status": "draft"}}
            update_response = requests.put(update_url, headers=HEADERS, json=update_data, timeout=10)
            
            if update_response.status_code == 200:
                draft_count += 1
        
        print(f"Drafted {len(products)} (total: {draft_count})")
    
    print(f"📝 Drafted {draft_count} products")
    
    # Step 2: Delete all draft products
    print("\n🗑️ Step 2: Deleting all draft products...")
    
    delete_count = 0
    
    while True:
        # Get 100 draft products
        url = f"https://{SHOP_DOMAIN}/admin/api/2023-10/products.json?limit=100&status=draft"
        response = requests.get(url, headers=HEADERS, timeout=30)
        
        if response.status_code != 200:
            print(f"❌ Error: {response.status_code}")
            break
        
        data = response.json()
        products = data["products"]
        
        if not products:
            print("✅ No more draft products to delete!")
            break
        
        print(f"Deleting {len(products)} draft products...")
        
        # Delete each
        for product in products:
            product_id = product["id"]
            delete_url = f"https://{SHOP_DOMAIN}/admin/api/2023-10/products/{product_id}.json"
            delete_response = requests.delete(delete_url, headers=HEADERS, timeout=10)
            
            if delete_response.status_code == 200:
                delete_count += 1
        
        print(f"Deleted {len(products)} (total: {delete_count})")
    
    # Final check
    count_response = requests.get(count_url, headers=HEADERS, timeout=30)
    final_count = count_response.json()["count"]
    
    print(f"\n🎉 DONE!")
    print(f"Drafted: {draft_count}")
    print(f"Deleted: {delete_count}")
    print(f"Remaining: {final_count}")

if __name__ == "__main__":
    draft_then_delete() 