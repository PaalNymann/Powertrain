#!/usr/bin/env python3
"""
Reassign ALL Products to Correct Collections
1. Remove all existing collection assignments
2. Assign all products based on their Rackbeat group (product_group metafield)
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

def get_all_product_collections(product_id):
    """Get all collections for a product"""
    url = f"https://{SHOPIFY_DOMAIN}/admin/api/2023-10/collects.json"
    headers = get_shopify_headers()
    params = {'product_id': product_id}
    
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json().get('collects', [])
    return []

def remove_product_from_collection(collect_id):
    """Remove a product from a collection by collect ID"""
    url = f"https://{SHOPIFY_DOMAIN}/admin/api/2023-10/collects/{collect_id}.json"
    headers = get_shopify_headers()
    
    response = requests.delete(url, headers=headers)
    return response.status_code == 200

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
    print("🚀 Starting Complete Collection Reassignment Based on Rackbeat Groups...")
    
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
    print(f"\n📦 STEP 2: Getting products with Rackbeat groups...")
    products = get_products_with_rackbeat_groups()
    
    if not products:
        print("❌ No products found with Rackbeat groups!")
        return
    
    # Step 3: Remove all existing collection assignments
    print(f"\n🗑️  STEP 3: Removing all existing collection assignments...")
    
    removed_collections = 0
    
    for i, (product_id, title, handle, rackbeat_group) in enumerate(products):
        if i % 20 == 0:
            print(f"  Progress: {i+1}/{len(products)} - removing existing collections...")
        
        # Get all current collections for this product
        current_collects = get_all_product_collections(product_id)
        
        # Remove from all collections
        for collect in current_collects:
            collect_id = collect['id']
            if remove_product_from_collection(collect_id):
                removed_collections += 1
        
        # Small delay to avoid rate limiting
        time.sleep(0.1)
    
    print(f"✅ Removed {removed_collections} collection assignments")
    
    # Step 4: Assign all products based on Rackbeat group
    print(f"\n🔄 STEP 4: Assigning all products based on Rackbeat group...")
    
    drivaksel_assigned = 0
    mellomaksel_assigned = 0
    failed_assignments = 0
    
    for i, (product_id, title, handle, rackbeat_group) in enumerate(products):
        print(f"📦 [{i+1}/{len(products)}] Assigning: {title[:50]}... (Group: {rackbeat_group})")
        
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
        
        # Delay to avoid rate limiting
        time.sleep(0.3)
    
    # Final results
    print(f"\n📊 COMPLETE REASSIGNMENT RESULTS:")
    print(f"  🗑️  Collections removed: {removed_collections}")
    print(f"  🔧 Drivaksel → Drivaksler: {drivaksel_assigned}")
    print(f"  ⚙️  Mellomaksel → Mellomaksler: {mellomaksel_assigned}")
    print(f"  ✅ Total successful assignments: {drivaksel_assigned + mellomaksel_assigned}")
    print(f"  ❌ Failed assignments: {failed_assignments}")
    
    total_expected = len(products)
    total_assigned = drivaksel_assigned + mellomaksel_assigned
    
    print(f"\n🎯 FINAL STATUS: {total_assigned}/{total_expected} products correctly assigned")
    
    if total_assigned == total_expected:
        print(f"\n🎉 ALL PRODUCTS SUCCESSFULLY REASSIGNED BASED ON RACKBEAT GROUPS!")
        print(f"Every product is now in the correct collection according to its Rackbeat group.")
    elif failed_assignments == 0:
        print(f"\n✅ REASSIGNMENT COMPLETED! All products processed successfully.")
    else:
        print(f"\n⚠️  {failed_assignments} assignments failed - may need retry")
    
    return {
        'removed_collections': removed_collections,
        'drivaksel_assigned': drivaksel_assigned,
        'mellomaksel_assigned': mellomaksel_assigned,
        'total_assigned': total_assigned,
        'failed': failed_assignments,
        'total_products': total_expected
    }

if __name__ == "__main__":
    result = main()
    print(f"\n📊 FINAL SUMMARY:")
    print(json.dumps(result, indent=2))
