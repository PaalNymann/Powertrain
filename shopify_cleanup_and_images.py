#!/usr/bin/env python3
"""
Shopify Cleanup and Bulk Image Update Script
1. Remove excess products (keep only eligible Drivaksel/Mellomaksel)
2. Bulk update images for remaining products
"""

import os
import requests
import json
from dotenv import load_dotenv
from database import SessionLocal

# Load environment variables
load_dotenv()

SHOPIFY_DOMAIN = os.getenv('SHOPIFY_DOMAIN')
SHOPIFY_TOKEN = os.getenv('SHOPIFY_TOKEN')

def get_shopify_headers():
    return {
        'X-Shopify-Access-Token': SHOPIFY_TOKEN,
        'Content-Type': 'application/json'
    }

def get_all_shopify_products():
    """Get all products from Shopify"""
    url = f"https://{SHOPIFY_DOMAIN}/admin/api/2023-10/products.json"
    headers = get_shopify_headers()
    
    all_products = []
    params = {'limit': 250}
    
    while True:
        print(f"Fetching products from Shopify... (current count: {len(all_products)})")
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code != 200:
            print(f"Error fetching products: {response.status_code} - {response.text}")
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
    
    print(f"Total Shopify products found: {len(all_products)}")
    return all_products

def get_eligible_product_ids_from_db():
    """Get list of product IDs that should remain in Shopify (from Railway DB)"""
    from database import ShopifyProduct
    
    session = SessionLocal()
    try:
        # Get all products that are in our Railway database (these are the eligible ones)
        products = session.query(ShopifyProduct).all()
        eligible_ids = [product.id for product in products]
        
        print(f"Eligible products in Railway DB: {len(eligible_ids)}")
        return set(eligible_ids)
    finally:
        session.close()

def delete_shopify_product(product_id):
    """Delete a product from Shopify"""
    url = f"https://{SHOPIFY_DOMAIN}/admin/api/2023-10/products/{product_id}.json"
    headers = get_shopify_headers()
    
    response = requests.delete(url, headers=headers)
    return response.status_code == 200

def get_product_collections(product_id):
    """Get collections for a product"""
    url = f"https://{SHOPIFY_DOMAIN}/admin/api/2023-10/products/{product_id}.json"
    headers = get_shopify_headers()
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        product_data = response.json()
        # Check if product is in Drivaksler or Mellomaksler collections
        # We'll need to check collections separately
        return product_data.get('product', {})
    return None

def get_collections():
    """Get all collections from Shopify"""
    url = f"https://{SHOPIFY_DOMAIN}/admin/api/2023-10/custom_collections.json"
    headers = get_shopify_headers()
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get('custom_collections', [])
    return []

def update_product_image(product_id, image_url):
    """Update product image in Shopify"""
    url = f"https://{SHOPIFY_DOMAIN}/admin/api/2023-10/products/{product_id}.json"
    headers = get_shopify_headers()
    
    # First get current product data
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        return False
        
    product_data = response.json().get('product', {})
    
    # Update with new image
    update_data = {
        "product": {
            "id": product_id,
            "images": [
                {
                    "src": image_url,
                    "alt": product_data.get('title', '')
                }
            ]
        }
    }
    
    response = requests.put(url, headers=headers, json=update_data)
    return response.status_code == 200

def main():
    print("🚀 Starting Shopify Cleanup and Bulk Image Update...")
    
    # Step 1: Get current state
    print("\n📊 STEP 1: Analyzing current Shopify catalog...")
    shopify_products = get_all_shopify_products()
    eligible_ids = get_eligible_product_ids_from_db()
    
    # Step 2: Identify products to remove
    products_to_remove = []
    products_to_keep = []
    
    for product in shopify_products:
        product_id = str(product['id'])
        if product_id in eligible_ids:
            products_to_keep.append(product)
        else:
            products_to_remove.append(product)
    
    print(f"\n📈 ANALYSIS RESULTS:")
    print(f"  Total products in Shopify: {len(shopify_products)}")
    print(f"  Products to keep: {len(products_to_keep)}")
    print(f"  Products to remove: {len(products_to_remove)}")
    
    # Step 3: Show some examples of products to remove
    if products_to_remove:
        print(f"\n🗑️  EXAMPLES OF PRODUCTS TO REMOVE:")
        for i, product in enumerate(products_to_remove[:5]):
            print(f"  - {product['id']}: {product['title']}")
        if len(products_to_remove) > 5:
            print(f"  ... and {len(products_to_remove) - 5} more")
    
    # Step 4: Get collections info
    print(f"\n📂 STEP 2: Analyzing collections...")
    collections = get_collections()
    drivaksler_collection = None
    mellomaksler_collection = None
    
    for collection in collections:
        if collection['handle'] == 'drivaksler':
            drivaksler_collection = collection
        elif collection['handle'] == 'mellomaksler':
            mellomaksler_collection = collection
    
    print(f"  Drivaksler collection: {drivaksler_collection['title'] if drivaksler_collection else 'NOT FOUND'}")
    print(f"  Mellomaksler collection: {mellomaksler_collection['title'] if mellomaksler_collection else 'NOT FOUND'}")
    
    # Step 5: Ask user for confirmation and image URLs
    print(f"\n🎯 READY FOR CLEANUP AND IMAGE UPDATE!")
    print(f"This will:")
    print(f"  1. Remove {len(products_to_remove)} excess products from Shopify")
    print(f"  2. Keep {len(products_to_keep)} eligible products")
    print(f"  3. Update images for remaining products")
    
    # For now, just show the analysis
    print(f"\n✅ Analysis complete! Ready for user confirmation.")
    
    return {
        'total_products': len(shopify_products),
        'products_to_keep': len(products_to_keep),
        'products_to_remove': len(products_to_remove),
        'drivaksler_found': drivaksler_collection is not None,
        'mellomaksler_found': mellomaksler_collection is not None
    }

if __name__ == "__main__":
    result = main()
    print(f"\n📊 SUMMARY:")
    print(json.dumps(result, indent=2))
