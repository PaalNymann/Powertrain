#!/usr/bin/env python3
"""
Quick Collection Verification
Just count how many products are in each collection
"""

import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SHOPIFY_DOMAIN = os.getenv('SHOPIFY_DOMAIN')
SHOPIFY_TOKEN = os.getenv('SHOPIFY_TOKEN')

def get_shopify_headers():
    return {
        'X-Shopify-Access-Token': SHOPIFY_TOKEN,
        'Content-Type': 'application/json'
    }

def get_collection_product_count(collection_id):
    """Get product count for a collection"""
    url = f"https://{SHOPIFY_DOMAIN}/admin/api/2023-10/collections/{collection_id}/products/count.json"
    headers = get_shopify_headers()
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get('count', 0)
    return 0

def main():
    print("🔍 Quick Collection Verification...")
    
    # Get collections
    url = f"https://{SHOPIFY_DOMAIN}/admin/api/2023-10/custom_collections.json"
    headers = get_shopify_headers()
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        collections = response.json().get('custom_collections', [])
        
        print(f"\n📊 COLLECTION PRODUCT COUNTS:")
        
        total_in_collections = 0
        
        for collection in collections:
            count = get_collection_product_count(collection['id'])
            total_in_collections += count
            
            # Highlight our target collections
            if 'drivaksler' in collection['title'].lower():
                print(f"  🔧 {collection['title']}: {count} produkter")
            elif 'mellomaksler' in collection['title'].lower():
                print(f"  ⚙️  {collection['title']}: {count} produkter")
            else:
                print(f"  📦 {collection['title']}: {count} produkter")
        
        print(f"\n📊 TOTALT I COLLECTIONS: {total_in_collections}")
        
        # Get total products in store
        url = f"https://{SHOPIFY_DOMAIN}/admin/api/2023-10/products/count.json"
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            total_products = response.json().get('count', 0)
            print(f"📦 TOTALT PRODUKTER I BUTIKK: {total_products}")
            
            if total_products == 156:
                print(f"✅ RIKTIG ANTALL PRODUKTER I BUTIKK!")
            else:
                print(f"⚠️  Forventet 156 produkter, fant {total_products}")
    
    else:
        print(f"❌ Kunne ikke hente collections: {response.status_code}")

if __name__ == "__main__":
    main()
