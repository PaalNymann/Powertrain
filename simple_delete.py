#!/usr/bin/env python3
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

def simple_delete():
    print("🗑️ SIMPLE DELETE")
    print("=" * 20)
    
    # Get count
    count_url = f"https://{SHOP_DOMAIN}/admin/api/2023-10/products/count.json"
    count_response = requests.get(count_url, headers=HEADERS, timeout=30)
    current_count = count_response.json()["count"]
    
    print(f"Products: {current_count}")
    
    if current_count == 0:
        print("✅ Done!")
        return
    
    # Confirm
    response = input(f"Delete all {current_count} products? (type 'YES'): ")
    if response != "YES":
        print("❌ Cancelled.")
        return
    
    # Delete in batches
    deleted = 0
    
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
            print("✅ No more products!")
            break
        
        print(f"Deleting {len(products)} products...")
        
        # Delete each
        for product in products:
            product_id = product["id"]
            delete_url = f"https://{SHOP_DOMAIN}/admin/api/2023-10/products/{product_id}.json"
            delete_response = requests.delete(delete_url, headers=HEADERS, timeout=10)
            
            if delete_response.status_code == 200:
                deleted += 1
        
        print(f"Deleted {len(products)} (total: {deleted})")
    
    # Final check
    count_response = requests.get(count_url, headers=HEADERS, timeout=30)
    final_count = count_response.json()["count"]
    
    print(f"\n🎉 DONE!")
    print(f"Deleted: {deleted}")
    print(f"Remaining: {final_count}")

if __name__ == "__main__":
    simple_delete() 