#!/usr/bin/env python3
"""
Fix Shopify Collection Assignment Based on Rackbeat Groups
- All products from Rackbeat group "Mellomaksel" → Shopify collection "Mellomaksler"
- All products from Rackbeat group "Drivaksel" → Shopify collection "Drivaksler"
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

def get_shopify_headers():
    return {
        'X-Shopify-Access-Token': SHOPIFY_TOKEN,
        'Content-Type': 'application/json'
    }

def get_shopify_collections():
    """Get Shopify collections and their IDs"""
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
        
        # Get all products with their Rackbeat group from metafields
        query = """
        SELECT sp.id, sp.title, sp.handle, 
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

def get_shopify_product_collections(product_id):
    """Get current collections for a Shopify product"""
    url = f"https://{SHOPIFY_DOMAIN}/admin/api/2023-10/products/{product_id}/collects.json"
    headers = get_shopify_headers()
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get('collects', [])
    return []

def remove_product_from_collection(product_id, collection_id):
    """Remove a product from a collection"""
    # First get the collect ID
    url = f"https://{SHOPIFY_DOMAIN}/admin/api/2023-10/collects.json"
    headers = get_shopify_headers()
    params = {'product_id': product_id, 'collection_id': collection_id}
    
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        collects = response.json().get('collects', [])
        for collect in collects:
            collect_id = collect['id']
            delete_url = f"https://{SHOPIFY_DOMAIN}/admin/api/2023-10/collects/{collect_id}.json"
            delete_response = requests.delete(delete_url, headers=headers)
            return delete_response.status_code == 200
    return False

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
    print("🚀 Starting Collection Assignment Based on Rackbeat Groups...")
    
    # Step 1: Get collections
    print("\n📂 STEP 1: Getting Shopify collections...")
    drivaksler_collection, mellomaksler_collection = get_shopify_collections()
    
    if not drivaksler_collection or not mellomaksler_collection:
        print("❌ Could not find Drivaksler or Mellomaksler collections!")
        return
    
    print(f"✅ Found collections:")
    print(f"  - Drivaksler: {drivaksler_collection['id']} ({drivaksler_collection['title']})")
    print(f"  - Mellomaksler: {mellomaksler_collection['id']} ({mellomaksler_collection['title']})")
    
    # Step 2: Get products with Rackbeat groups
    print(f"\n📦 STEP 2: Getting products with Rackbeat groups from Railway DB...")
    products = get_products_with_rackbeat_groups()
    
    if not products:
        print("❌ No products found with Rackbeat groups!")
        return
    
    # Step 3: Assign products based on Rackbeat group
    print(f"\n🔄 STEP 3: Assigning products to collections based on Rackbeat group...")
    
    drivaksel_assigned = 0
    mellomaksel_assigned = 0
    failed_assignments = 0
    
    for product_id, title, handle, rackbeat_group in products:
        print(f"📦 Processing: {title[:60]}... (Group: {rackbeat_group})")
        
        if rackbeat_group == 'Drivaksel':
            target_collection = drivaksler_collection
            collection_name = 'Drivaksler'
        elif rackbeat_group == 'Mellomaksel':
            target_collection = mellomaksler_collection
            collection_name = 'Mellomaksler'
        else:
            print(f"  ❓ Unknown group: {rackbeat_group}")
            continue
        
        # Add delay to avoid rate limiting
        import time
        time.sleep(0.5)
        
        # Check if already assigned to correct collection
        current_collects = get_shopify_product_collections(product_id)
        already_assigned = any(collect['collection_id'] == target_collection['id'] for collect in current_collects)
        
        if already_assigned:
            print(f"  ✅ Already in {collection_name} collection")
            if rackbeat_group == 'Drivaksel':
                drivaksel_assigned += 1
            else:
                mellomaksel_assigned += 1
            continue
        
        # Remove from wrong collections first
        for collect in current_collects:
            wrong_collection_id = collect['collection_id']
            if wrong_collection_id != target_collection['id']:
                print(f"  🗑️  Removing from wrong collection {wrong_collection_id}")
                remove_product_from_collection(product_id, wrong_collection_id)
        
        # Assign to correct collection
        print(f"  ➕ Assigning to {collection_name} collection...")
        if assign_product_to_collection(product_id, target_collection['id']):
            if rackbeat_group == 'Drivaksel':
                drivaksel_assigned += 1
            else:
                mellomaksel_assigned += 1
            print(f"  ✅ Successfully assigned to {collection_name}")
        else:
            failed_assignments += 1
            print(f"  ❌ Failed to assign to {collection_name}")
    
    # Final results
    print(f"\n📊 COLLECTION ASSIGNMENT RESULTS (by Rackbeat Group):")
    print(f"  Drivaksel → Drivaksler: {drivaksel_assigned}")
    print(f"  Mellomaksel → Mellomaksler: {mellomaksel_assigned}")
    print(f"  Failed assignments: {failed_assignments}")
    print(f"  Total successful: {drivaksel_assigned + mellomaksel_assigned}")
    
    if (drivaksel_assigned + mellomaksel_assigned) > 0:
        print(f"\n✅ Collection assignment by Rackbeat group completed successfully!")
        print(f"All products are now assigned based on their original Rackbeat group.")
    else:
        print(f"\n❌ No products were assigned. Check API permissions and data.")
    
    return {
        'drivaksel_assigned': drivaksel_assigned,
        'mellomaksel_assigned': mellomaksel_assigned,
        'failed': failed_assignments,
        'total_assigned': drivaksel_assigned + mellomaksel_assigned
    }

if __name__ == "__main__":
    result = main()
    print(f"\n📊 FINAL SUMMARY:")
    print(json.dumps(result, indent=2))
