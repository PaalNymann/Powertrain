#!/usr/bin/env python3
"""
Bulk Image Update Script for Shopify Products
Update all Drivaksel products with one image, all Mellomaksel products with another
"""

import os
import requests
import json
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SHOPIFY_DOMAIN = os.getenv('SHOPIFY_DOMAIN')
SHOPIFY_TOKEN = os.getenv('SHOPIFY_TOKEN')
DATABASE_URL = 'postgresql://postgres:pmTNRdLNPAwZTYvtBFsqvfmjUOoNEuqM@shinkansen.proxy.rlwy.net:13074/railway'

# Image URLs provided by user
DRIVAKSEL_IMAGE_URL = "https://cdn.shopify.com/s/files/1/0715/2615/4389/files/Drivaksel_firk.png?v=1745401674"
MELLOMAKSEL_IMAGE_URL = "https://cdn.shopify.com/s/files/1/0715/2615/4389/files/Mellomaksel_firk.png?v=1745401674"

def get_shopify_headers():
    return {
        'X-Shopify-Access-Token': SHOPIFY_TOKEN,
        'Content-Type': 'application/json'
    }

def get_eligible_products_by_collection():
    """Get eligible products from Railway PostgreSQL grouped by collection"""
    try:
        print("🔗 Connecting to Railway PostgreSQL...")
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # Get all products with their metafields to determine collection
        query = """
        SELECT DISTINCT sp.id, sp.title, pm.value as original_nummer
        FROM shopify_products sp
        LEFT JOIN product_metafields pm ON sp.id = pm.product_id 
        WHERE pm.key = 'Original_nummer'
        """
        
        cursor.execute(query)
        products = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        print(f"✅ Found {len(products)} products with Original_nummer metafields")
        return products
    except Exception as e:
        print(f"❌ Database error: {e}")
        return []

def get_shopify_collections():
    """Get Shopify collections to identify Drivaksler and Mellomaksler"""
    url = f"https://{SHOPIFY_DOMAIN}/admin/api/2023-10/custom_collections.json"
    headers = get_shopify_headers()
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        collections = response.json().get('custom_collections', [])
        
        drivaksler_collection = None
        mellomaksler_collection = None
        
        print(f"🔍 Found {len(collections)} collections:")
        for collection in collections:
            handle = collection['handle'].lower()
            title = collection['title'].lower()
            print(f"  - {collection['title']} (handle: {collection['handle']})")
            
            if 'drivaksler' in handle or 'drivaksler' in title:
                drivaksler_collection = collection
            elif 'mellomaksler' in handle or 'mellomaksler' in title:
                mellomaksler_collection = collection
        
        return drivaksler_collection, mellomaksler_collection
    return None, None

def get_products_in_collection(collection_id):
    """Get all products in a specific collection"""
    url = f"https://{SHOPIFY_DOMAIN}/admin/api/2023-10/collections/{collection_id}/products.json"
    headers = get_shopify_headers()
    
    all_products = []
    params = {'limit': 250}
    
    while True:
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code != 200:
            print(f"Error fetching collection products: {response.status_code}")
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

def update_product_image(product_id, image_url, product_title):
    """Update product image in Shopify"""
    url = f"https://{SHOPIFY_DOMAIN}/admin/api/2023-10/products/{product_id}.json"
    headers = get_shopify_headers()
    
    # Update with new image
    update_data = {
        "product": {
            "id": product_id,
            "images": [
                {
                    "src": image_url,
                    "alt": product_title
                }
            ]
        }
    }
    
    response = requests.put(url, headers=headers, json=update_data)
    if response.status_code == 200:
        print(f"✅ Updated image for {product_id}: {product_title[:50]}")
        return True
    else:
        print(f"❌ Failed to update image for {product_id}: {response.status_code}")
        return False

def main():
    print("🚀 Starting Bulk Image Update for Shopify Products...")
    
    # Step 1: Get collections
    print("\n📂 STEP 1: Getting Shopify collections...")
    drivaksler_collection, mellomaksler_collection = get_shopify_collections()
    
    if not drivaksler_collection or not mellomaksler_collection:
        print("❌ Could not find Drivaksler or Mellomaksler collections!")
        return
    
    print(f"✅ Found collections:")
    print(f"  - Drivaksler: {drivaksler_collection['id']} ({drivaksler_collection['title']})")
    print(f"  - Mellomaksler: {mellomaksler_collection['id']} ({mellomaksler_collection['title']})")
    
    # Step 2: Get products in each collection
    print(f"\n📦 STEP 2: Getting products in collections...")
    
    drivaksler_products = get_products_in_collection(drivaksler_collection['id'])
    mellomaksler_products = get_products_in_collection(mellomaksler_collection['id'])
    
    print(f"✅ Found products:")
    print(f"  - Drivaksler: {len(drivaksler_products)} products")
    print(f"  - Mellomaksler: {len(mellomaksler_products)} products")
    
    # Step 3: Update images for Drivaksler products
    print(f"\n🖼️  STEP 3: Updating images for Drivaksler products...")
    drivaksler_updated = 0
    drivaksler_failed = 0
    
    for product in drivaksler_products:
        if update_product_image(product['id'], DRIVAKSEL_IMAGE_URL, product['title']):
            drivaksler_updated += 1
        else:
            drivaksler_failed += 1
    
    # Step 4: Update images for Mellomaksler products
    print(f"\n🖼️  STEP 4: Updating images for Mellomaksler products...")
    mellomaksler_updated = 0
    mellomaksler_failed = 0
    
    for product in mellomaksler_products:
        if update_product_image(product['id'], MELLOMAKSEL_IMAGE_URL, product['title']):
            mellomaksler_updated += 1
        else:
            mellomaksler_failed += 1
    
    # Final results
    print(f"\n📊 BULK IMAGE UPDATE RESULTS:")
    print(f"  Drivaksler products:")
    print(f"    - Successfully updated: {drivaksler_updated}")
    print(f"    - Failed to update: {drivaksler_failed}")
    print(f"  Mellomaksler products:")
    print(f"    - Successfully updated: {mellomaksler_updated}")
    print(f"    - Failed to update: {mellomaksler_failed}")
    print(f"  Total updated: {drivaksler_updated + mellomaksler_updated}")
    
    if (drivaksler_updated + mellomaksler_updated) > 0:
        print(f"\n✅ Bulk image update completed successfully!")
    else:
        print(f"\n❌ No images were updated. Check API permissions.")
    
    return {
        'drivaksler_updated': drivaksler_updated,
        'drivaksler_failed': drivaksler_failed,
        'mellomaksler_updated': mellomaksler_updated,
        'mellomaksler_failed': mellomaksler_failed,
        'total_updated': drivaksler_updated + mellomaksler_updated
    }

if __name__ == "__main__":
    result = main()
    print(f"\n📊 FINAL SUMMARY:")
    print(json.dumps(result, indent=2))
