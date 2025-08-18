#!/usr/bin/env python3
"""
Bulk Delete All Shopify Products + Sync Eligible Products
1. Delete ALL products from Shopify (bulk operation)
2. Sync only the 156 eligible products from Railway DB to Shopify
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

def get_all_shopify_product_ids():
    """Get all product IDs from Shopify for bulk deletion"""
    url = f"https://{SHOPIFY_DOMAIN}/admin/api/2023-10/products.json"
    headers = get_shopify_headers()
    
    all_product_ids = []
    params = {'limit': 250, 'fields': 'id'}
    
    while True:
        print(f"Fetching product IDs... (current count: {len(all_product_ids)})")
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code != 200:
            print(f"Error fetching products: {response.status_code}")
            break
            
        data = response.json()
        products = data.get('products', [])
        
        if not products:
            break
            
        all_product_ids.extend([str(p['id']) for p in products])
        
        # Check for pagination
        link_header = response.headers.get('Link', '')
        if 'rel="next"' not in link_header:
            break
            
        # Extract next page URL
        for link in link_header.split(','):
            if 'rel="next"' in link:
                next_url = link.split('<')[1].split('>')[0]
                url = next_url
                params = {'fields': 'id'}
                break
    
    print(f"Total product IDs found: {len(all_product_ids)}")
    return all_product_ids

def bulk_delete_shopify_products(product_ids, batch_size=100):
    """Delete products in batches"""
    headers = get_shopify_headers()
    deleted_count = 0
    failed_count = 0
    
    for i in range(0, len(product_ids), batch_size):
        batch = product_ids[i:i+batch_size]
        print(f"Deleting batch {i//batch_size + 1}: {len(batch)} products...")
        
        for product_id in batch:
            url = f"https://{SHOPIFY_DOMAIN}/admin/api/2023-10/products/{product_id}.json"
            response = requests.delete(url, headers=headers)
            
            if response.status_code == 200:
                deleted_count += 1
                if deleted_count % 50 == 0:
                    print(f"  Deleted {deleted_count}/{len(product_ids)} products...")
            else:
                failed_count += 1
                print(f"  Failed to delete {product_id}: {response.status_code}")
        
        # Smaller delay to avoid rate limiting
        time.sleep(0.1)
    
    return deleted_count, failed_count

def get_eligible_products_from_railway():
    """Get all eligible products from Railway PostgreSQL"""
    try:
        print("🔗 Connecting to Railway PostgreSQL...")
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # Get all products with their metafields
        query = """
        SELECT sp.id, sp.title, sp.handle, sp.sku, sp.price, sp.inventory_quantity,
               array_agg(pm.key || ':' || pm.value) as metafields
        FROM shopify_products sp
        LEFT JOIN product_metafields pm ON sp.id = pm.product_id
        GROUP BY sp.id, sp.title, sp.handle, sp.sku, sp.price, sp.inventory_quantity
        ORDER BY sp.title
        """
        
        cursor.execute(query)
        products = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        print(f"✅ Found {len(products)} eligible products in Railway DB")
        return products
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        return []

def create_shopify_product(product_data, metafields):
    """Create a single product in Shopify with metafields"""
    headers = get_shopify_headers()
    url = f"https://{SHOPIFY_DOMAIN}/admin/api/2023-10/products.json"
    
    # Determine collection based on title
    collection_id = None
    if 'drivaksel' in product_data['title'].lower():
        collection_id = "462858436885"  # Drivaksler collection ID
    elif 'mellomaksel' in product_data['title'].lower():
        collection_id = "462858469653"  # Mellomaksler collection ID
    
    # Create product payload
    product_payload = {
        "product": {
            "id": product_data['id'],
            "title": product_data['title'],
            "handle": product_data['handle'],
            "variants": [{
                "sku": product_data['sku'],
                "price": str(product_data['price']) if product_data['price'] else "0",
                "inventory_quantity": product_data['inventory_quantity'] or 0,
                "inventory_management": "shopify"
            }],
            "metafields": []
        }
    }
    
    # Add metafields
    for metafield in metafields:
        if metafield and ':' in metafield:
            key, value = metafield.split(':', 1)
            if key and value and value != 'None':
                product_payload["product"]["metafields"].append({
                    "namespace": "custom",
                    "key": key,
                    "value": value,
                    "type": "single_line_text_field"
                })
    
    # Create product
    response = requests.post(url, headers=headers, json=product_payload)
    
    if response.status_code == 201:
        product_id = response.json()['product']['id']
        
        # Add to collection if applicable
        if collection_id:
            collect_url = f"https://{SHOPIFY_DOMAIN}/admin/api/2023-10/collects.json"
            collect_payload = {
                "collect": {
                    "product_id": product_id,
                    "collection_id": collection_id
                }
            }
            requests.post(collect_url, headers=headers, json=collect_payload)
        
        return True
    else:
        print(f"Failed to create product {product_data['id']}: {response.status_code} - {response.text[:100]}")
        return False

def sync_products_to_shopify(products):
    """Sync all eligible products to Shopify"""
    created_count = 0
    failed_count = 0
    
    for i, product_row in enumerate(products):
        product_id, title, handle, sku, price, inventory_quantity, metafields = product_row
        
        print(f"Creating {i+1}/{len(products)}: {title[:50]}...")
        
        product_data = {
            'id': product_id,
            'title': title,
            'handle': handle,
            'sku': sku,
            'price': price,
            'inventory_quantity': inventory_quantity
        }
        
        if create_shopify_product(product_data, metafields or []):
            created_count += 1
        else:
            failed_count += 1
        
        # Progress update
        if (i + 1) % 10 == 0:
            print(f"  Progress: {i+1}/{len(products)} ({created_count} created, {failed_count} failed)")
        
        # Small delay to avoid rate limiting
        time.sleep(0.2)
    
    return created_count, failed_count

def main():
    print("🚀 Starting Bulk Delete + Sync Operation...")
    
    # Step 1: Get all Shopify product IDs
    print("\n🗑️  STEP 1: Getting all Shopify product IDs for deletion...")
    product_ids = get_all_shopify_product_ids()
    
    if not product_ids:
        print("No products found in Shopify to delete.")
    else:
        # Step 2: Bulk delete all products
        print(f"\n🗑️  STEP 2: Bulk deleting {len(product_ids)} products from Shopify...")
        deleted, failed_deletes = bulk_delete_shopify_products(product_ids)
        print(f"Deletion complete: {deleted} deleted, {failed_deletes} failed")
    
    # Step 3: Get eligible products from Railway
    print(f"\n📦 STEP 3: Getting eligible products from Railway DB...")
    eligible_products = get_eligible_products_from_railway()
    
    if not eligible_products:
        print("❌ No eligible products found in Railway DB!")
        return
    
    # Step 4: Sync products to Shopify
    print(f"\n📦 STEP 4: Syncing {len(eligible_products)} products to Shopify...")
    created, failed_creates = sync_products_to_shopify(eligible_products)
    
    # Final results
    print(f"\n📊 BULK DELETE + SYNC RESULTS:")
    print(f"  Shopify products deleted: {deleted if 'deleted' in locals() else 0}")
    print(f"  Failed deletions: {failed_deletes if 'failed_deletes' in locals() else 0}")
    print(f"  Products created: {created}")
    print(f"  Failed creations: {failed_creates}")
    
    if created > 0:
        print(f"\n✅ Bulk delete + sync completed successfully!")
        print(f"Shopify now contains only the {created} eligible Drivaksel/Mellomaksel products.")
    else:
        print(f"\n❌ No products were created. Check API permissions and data.")

if __name__ == "__main__":
    main()
