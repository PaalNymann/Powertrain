#!/usr/bin/env python3
"""
Direct Collect Verification
Check collects directly instead of collection counts
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

def get_all_collects():
    """Get all collects directly"""
    url = f"https://{SHOPIFY_DOMAIN}/admin/api/2023-10/collects.json"
    headers = get_shopify_headers()
    
    all_collects = []
    params = {'limit': 250}
    
    while True:
        print(f"Fetching collects... (current count: {len(all_collects)})")
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code != 200:
            print(f"Error fetching collects: {response.status_code}")
            break
            
        data = response.json()
        collects = data.get('collects', [])
        
        if not collects:
            break
            
        all_collects.extend(collects)
        
        # Check for pagination
        link_header = response.headers.get('Link', '')
        if 'rel="next"' not in link_header:
            break
            
        # Extract next page URL
        for link in link_header.split(','):
            if 'rel="next"' in link:
                next_url = link.split('<')[1].split('>')[0]
                url = next_url
                params = {}
                break
    
    return all_collects

def main():
    print("🔍 Direct Collect Verification...")
    
    # Get all collects
    collects = get_all_collects()
    print(f"✅ Found {len(collects)} total collects")
    
    if not collects:
        print("❌ No collects found at all!")
        return
    
    # Count by collection ID
    collection_counts = {}
    
    # Known collection IDs
    drivaksler_id = "342889627797"
    mellomaksler_id = "342889496725"
    
    for collect in collects:
        collection_id = str(collect['collection_id'])
        if collection_id not in collection_counts:
            collection_counts[collection_id] = 0
        collection_counts[collection_id] += 1
    
    print(f"\n📊 COLLECT COUNTS BY COLLECTION ID:")
    for collection_id, count in collection_counts.items():
        if collection_id == drivaksler_id:
            print(f"  🔧 Drivaksler ({collection_id}): {count} produkter")
        elif collection_id == mellomaksler_id:
            print(f"  ⚙️  Mellomaksler ({collection_id}): {count} produkter")
        else:
            print(f"  📦 Other ({collection_id}): {count} produkter")
    
    # Show recent collects
    print(f"\n🕐 RECENT COLLECTS (last 10):")
    for collect in collects[-10:]:
        collection_id = str(collect['collection_id'])
        product_id = collect['product_id']
        
        if collection_id == drivaksler_id:
            print(f"  🔧 Product {product_id} → Drivaksler")
        elif collection_id == mellomaksler_id:
            print(f"  ⚙️  Product {product_id} → Mellomaksler")
        else:
            print(f"  📦 Product {product_id} → Other ({collection_id})")

if __name__ == "__main__":
    main()
