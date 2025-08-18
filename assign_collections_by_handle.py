#!/usr/bin/env python3
"""
Assign Collections Using Product Handles
Match Railway DB products to Shopify products via handle/SKU, then assign collections
"""

import os
import requests
import json
import psycopg2
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv()

SHOPIFY_DOMAIN = os.getenv('SHOPIFY_DOMAIN')
SHOPIFY_TOKEN = os.getenv('SHOPIFY_TOKEN')
DATABASE_URL = 'postgresql://postgres:pmTNRdLNPAwZTYvtBFsqvfmjUOoNEuqM@shinkansen.proxy.rlwy.net:13074/railway'

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

def get_products_with_rackbeat_groups():
    """Get all products from Railway DB with their Rackbeat groups"""
    try:
        print("🔗 Connecting to Railway PostgreSQL...")
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        query = """
        SELECT sp.id, sp.title, sp.handle, sp.sku,
               pm_group.value as rackbeat_group
        FROM shopify_products sp
        LEFT JOIN product_metafields pm_group ON sp.id = pm_group.product_id 
            AND pm_group.key = 'product_group'
        WHERE pm_group.value IN ('Drivaksel', 'Mellomaksel')
        ORDER BY pm_group.value, sp.title
        """
        
        cursor.execute(query)
        products = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        print(f"✅ Found {len(products)} products with Rackbeat groups")
        return products
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        return []

def get_all_shopify_products():
    """Get all products from Shopify with their real IDs"""
    url = f"https://{SHOPIFY_DOMAIN}/admin/api/2023-10/products.json"
    headers = get_shopify_headers()
    
    all_products = {}  # handle -> product_info
    params = {'limit': 250}
    
    while True:
        print(f"Fetching Shopify products... (current count: {len(all_products)})")
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code != 200:
            print(f"Error fetching products: {response.status_code}")
            break
            
        data = response.json()
        products = data.get('products', [])
        
        if not products:
            break
        
        for product in products:
            handle = product['handle']
            all_products[handle] = {
                'id': product['id'],
                'title': product['title'],
                'handle': handle
            }
            
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
    
    print(f"✅ Found {len(all_products)} Shopify products")
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
    print("🚀 Starting Collection Assignment Using Product Handles...")
    
    # Step 1: Get collections
    print("\n📂 STEP 1: Getting Shopify collections...")
    drivaksler_collection, mellomaksler_collection = get_shopify_collections()
    
    if not drivaksler_collection or not mellomaksler_collection:
        print("❌ Could not find Drivaksler or Mellomaksler collections!")
        return
    
    print(f"✅ Found collections:")
    print(f"  - Drivaksler: {drivaksler_collection['id']} ({drivaksler_collection['title']})")
    print(f"  - Mellomaksler: {mellomaksler_collection['id']} ({mellomaksler_collection['title']})")
    
    # Step 2: Get Railway products with groups
    print(f"\n📦 STEP 2: Getting products with Rackbeat groups from Railway DB...")
    railway_products = get_products_with_rackbeat_groups()
    
    if not railway_products:
        print("❌ No products found with Rackbeat groups!")
        return
    
    # Step 3: Get all Shopify products
    print(f"\n🛍️  STEP 3: Getting all Shopify products...")
    shopify_products = get_all_shopify_products()
    
    if not shopify_products:
        print("❌ No Shopify products found!")
        return
    
    # Step 4: Match and assign products
    print(f"\n🔄 STEP 4: Matching and assigning products to collections...")
    
    drivaksel_assigned = 0
    mellomaksel_assigned = 0
    failed_assignments = 0
    not_found = 0
    
    for db_id, title, handle, sku, rackbeat_group in railway_products:
        print(f"📦 Processing: {title[:50]}... (Group: {rackbeat_group})")
        
        # Find matching Shopify product by handle
        shopify_product = shopify_products.get(handle)
        
        if not shopify_product:
            print(f"  ❌ Product not found in Shopify by handle: {handle}")
            not_found += 1
            continue
        
        shopify_product_id = shopify_product['id']
        print(f"  ✅ Found Shopify product ID: {shopify_product_id}")
        
        # Determine target collection
        if rackbeat_group == 'Drivaksel':
            target_collection = drivaksler_collection
            collection_name = 'Drivaksler'
        elif rackbeat_group == 'Mellomaksel':
            target_collection = mellomaksler_collection
            collection_name = 'Mellomaksler'
        else:
            print(f"  ❓ Unknown group: {rackbeat_group}")
            failed_assignments += 1
            continue
        
        # Assign to collection
        print(f"  ➕ Assigning to {collection_name} collection...")
        if assign_product_to_collection(shopify_product_id, target_collection['id']):
            if rackbeat_group == 'Drivaksel':
                drivaksel_assigned += 1
            else:
                mellomaksel_assigned += 1
            print(f"  ✅ Successfully assigned to {collection_name}")
        else:
            failed_assignments += 1
            print(f"  ❌ Failed to assign to {collection_name}")
        
        # Delay to avoid rate limiting
        time.sleep(0.2)
    
    # Final results
    print(f"\n📊 COLLECTION ASSIGNMENT RESULTS (by Handle Matching):")
    print(f"  🔧 Drivaksel → Drivaksler: {drivaksel_assigned}")
    print(f"  ⚙️  Mellomaksel → Mellomaksler: {mellomaksel_assigned}")
    print(f"  ✅ Total successful assignments: {drivaksel_assigned + mellomaksel_assigned}")
    print(f"  ❌ Failed assignments: {failed_assignments}")
    print(f"  ❓ Products not found in Shopify: {not_found}")
    
    total_expected = len(railway_products)
    total_assigned = drivaksel_assigned + mellomaksel_assigned
    
    print(f"\n🎯 FINAL STATUS: {total_assigned}/{total_expected} products correctly assigned")
    
    if total_assigned == total_expected:
        print(f"\n🎉 ALL PRODUCTS SUCCESSFULLY ASSIGNED BASED ON RACKBEAT GROUPS!")
        print(f"Every product is now in the correct collection according to its Rackbeat group.")
    elif failed_assignments == 0 and not_found == 0:
        print(f"\n✅ ASSIGNMENT COMPLETED! All found products processed successfully.")
    else:
        print(f"\n⚠️  Some assignments failed or products not found - may need investigation")
    
    return {
        'drivaksel_assigned': drivaksel_assigned,
        'mellomaksel_assigned': mellomaksel_assigned,
        'total_assigned': total_assigned,
        'failed': failed_assignments,
        'not_found': not_found,
        'total_products': total_expected
    }

if __name__ == "__main__":
    result = main()
    print(f"\n📊 FINAL SUMMARY:")
    print(json.dumps(result, indent=2))
