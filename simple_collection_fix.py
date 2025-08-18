#!/usr/bin/env python3
"""
Simple Collection Assignment Fix
Use Shopify API to get products with metafields, then assign based on product_group
"""

import os
import requests
import json
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv()

SHOPIFY_DOMAIN = os.getenv('SHOPIFY_DOMAIN')
SHOPIFY_TOKEN = os.getenv('SHOPIFY_TOKEN')

def get_shopify_headers():
    return {
        'X-Shopify-Access-Token': SHOPIFY_TOKEN,
        'Content-Type': 'application/json'
    }

def get_shopify_collections():
    """Get Shopify collections"""
    url = f"https://{SHOPIFY_DOMAIN}/admin/api/2023-10/custom_collections.json"
    headers = get_shopify_headers()
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        collections = response.json().get('custom_collections', [])
        
        drivaksler_collection = None
        mellomaksler_collection = None
        
        for collection in collections:
            handle = collection['handle'].lower()
            title = collection['title'].lower()
            if 'drivaksler' in handle or 'drivaksler' in title:
                drivaksler_collection = collection
            elif 'mellomaksler' in handle or 'mellomaksler' in title:
                mellomaksler_collection = collection
        
        return drivaksler_collection, mellomaksler_collection
    return None, None

def get_product_metafields(product_id):
    """Get metafields for a specific product"""
    url = f"https://{SHOPIFY_DOMAIN}/admin/api/2023-10/products/{product_id}/metafields.json"
    headers = get_shopify_headers()
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        metafields = response.json().get('metafields', [])
        
        # Look for product_group metafield
        for metafield in metafields:
            if metafield.get('key') == 'product_group':
                return metafield.get('value')
    
    return None

def get_all_shopify_products():
    """Get all products from Shopify"""
    url = f"https://{SHOPIFY_DOMAIN}/admin/api/2023-10/products.json"
    headers = get_shopify_headers()
    
    all_products = []
    params = {'limit': 250}
    
    while True:
        print(f"Fetching products... (current count: {len(all_products)})")
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code != 200:
            print(f"Error fetching products: {response.status_code}")
            break
            
        data = response.json()
        products = data.get('products', [])
        
        if not products:
            break
            
        all_products.extend(products)
        
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
    
    return all_products

def assign_product_to_collection(product_id, collection_id):
    """Assign a product to a collection"""
    url = f"https://{SHOPIFY_DOMAIN}/admin/api/2023-10/collects.json"
    headers = get_shopify_headers()
    
    payload = {
        "collect": {
            "product_id": product_id,
            "collection_id": collection_id
        }
    }
    
    response = requests.post(url, headers=headers, json=payload)
    return response.status_code == 201

def main():
    print("🚀 Starting Simple Collection Assignment Fix...")
    
    # Step 1: Get collections
    print("\n📂 STEP 1: Getting Shopify collections...")
    drivaksler_collection, mellomaksler_collection = get_shopify_collections()
    
    if not drivaksler_collection or not mellomaksler_collection:
        print("❌ Could not find Drivaksler or Mellomaksler collections!")
        return
    
    print(f"✅ Found collections:")
    print(f"  - Drivaksler: {drivaksler_collection['id']} ({drivaksler_collection['title']})")
    print(f"  - Mellomaksler: {mellomaksler_collection['id']} ({mellomaksler_collection['title']})")
    
    # Step 2: Get all products
    print(f"\n📦 STEP 2: Getting all Shopify products...")
    products = get_all_shopify_products()
    print(f"✅ Found {len(products)} products")
    
    # Step 3: Process products and assign based on metafield
    print(f"\n🔄 STEP 3: Assigning products based on product_group metafield...")
    
    drivaksel_assigned = 0
    mellomaksel_assigned = 0
    no_group = 0
    failed_assignments = 0
    
    for i, product in enumerate(products):
        product_id = product['id']
        title = product['title']
        
        print(f"📦 [{i+1}/{len(products)}] Processing: {title[:50]}...")
        
        # Get product_group metafield
        product_group = get_product_metafields(product_id)
        
        if not product_group:
            print(f"  ❓ No product_group metafield found")
            no_group += 1
            continue
        
        print(f"  📋 Product group: {product_group}")
        
        # Assign based on group
        if product_group == 'Drivaksel':
            print(f"  🔧 Assigning to Drivaksler collection...")
            if assign_product_to_collection(product_id, drivaksler_collection['id']):
                drivaksel_assigned += 1
                print(f"  ✅ Successfully assigned to Drivaksler")
            else:
                failed_assignments += 1
                print(f"  ❌ Failed to assign to Drivaksler")
                
        elif product_group == 'Mellomaksel':
            print(f"  ⚙️  Assigning to Mellomaksler collection...")
            if assign_product_to_collection(product_id, mellomaksler_collection['id']):
                mellomaksel_assigned += 1
                print(f"  ✅ Successfully assigned to Mellomaksler")
            else:
                failed_assignments += 1
                print(f"  ❌ Failed to assign to Mellomaksler")
        else:
            print(f"  ❓ Unknown group: {product_group}")
            no_group += 1
        
        # Delay to avoid rate limiting
        time.sleep(0.3)
    
    # Final results
    print(f"\n📊 COLLECTION ASSIGNMENT RESULTS:")
    print(f"  🔧 Drivaksel → Drivaksler: {drivaksel_assigned}")
    print(f"  ⚙️  Mellomaksel → Mellomaksler: {mellomaksel_assigned}")
    print(f"  ✅ Total successful assignments: {drivaksel_assigned + mellomaksel_assigned}")
    print(f"  ❌ Failed assignments: {failed_assignments}")
    print(f"  ❓ No group/other groups: {no_group}")
    
    total_assigned = drivaksel_assigned + mellomaksel_assigned
    
    if total_assigned > 0:
        print(f"\n🎉 COLLECTION ASSIGNMENT COMPLETED!")
        print(f"Products are now assigned based on their Rackbeat product_group metafield.")
    else:
        print(f"\n❌ No products were assigned. Check metafields and API permissions.")
    
    return {
        'drivaksel_assigned': drivaksel_assigned,
        'mellomaksel_assigned': mellomaksel_assigned,
        'total_assigned': total_assigned,
        'failed': failed_assignments,
        'no_group': no_group
    }

if __name__ == "__main__":
    result = main()
    print(f"\n📊 FINAL SUMMARY:")
    print(json.dumps(result, indent=2))
