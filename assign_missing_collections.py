#!/usr/bin/env python3
"""
Assign Missing Collection Products
Only assign products that are NOT already in any collection
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

def check_product_collections(product_id):
    """Check which collections a product belongs to"""
    url = f"https://{SHOPIFY_DOMAIN}/admin/api/2023-10/collects.json"
    headers = get_shopify_headers()
    params = {'product_id': product_id}
    
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json().get('collects', [])
    return []

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
    print("🚀 Starting Assignment of Missing Collection Products...")
    
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
    
    # Step 3: Find products without collections and assign them
    print(f"\n🔍 STEP 3: Finding products without collections...")
    
    unassigned_products = []
    already_assigned = 0
    
    for product_id, title, handle, rackbeat_group in products:
        print(f"🔍 Checking: {title[:50]}... (Group: {rackbeat_group})")
        
        # Check if product has any collections
        current_collects = check_product_collections(product_id)
        
        if not current_collects:
            print(f"  ❓ NO COLLECTIONS - needs assignment")
            unassigned_products.append((product_id, title, handle, rackbeat_group))
        else:
            print(f"  ✅ Already in {len(current_collects)} collection(s)")
            already_assigned += 1
        
        # Small delay to avoid rate limiting
        time.sleep(0.2)
    
    print(f"\n📊 COLLECTION STATUS:")
    print(f"  ✅ Already assigned: {already_assigned}")
    print(f"  ❓ Need assignment: {len(unassigned_products)}")
    
    if not unassigned_products:
        print(f"\n🎉 ALL PRODUCTS ARE ALREADY ASSIGNED TO COLLECTIONS!")
        return
    
    # Step 4: Assign unassigned products
    print(f"\n🔄 STEP 4: Assigning {len(unassigned_products)} unassigned products...")
    
    drivaksel_assigned = 0
    mellomaksel_assigned = 0
    failed_assignments = 0
    
    for product_id, title, handle, rackbeat_group in unassigned_products:
        print(f"📦 Assigning: {title[:50]}... (Group: {rackbeat_group})")
        
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
        time.sleep(0.5)
    
    # Final results
    print(f"\n📊 ASSIGNMENT RESULTS:")
    print(f"  🔧 Drivaksel → Drivaksler: {drivaksel_assigned}")
    print(f"  ⚙️  Mellomaksel → Mellomaksler: {mellomaksel_assigned}")
    print(f"  ✅ Total successful: {drivaksel_assigned + mellomaksel_assigned}")
    print(f"  ❌ Failed assignments: {failed_assignments}")
    print(f"  📊 Previously assigned: {already_assigned}")
    
    total_assigned = already_assigned + drivaksel_assigned + mellomaksel_assigned
    print(f"\n🎯 FINAL STATUS: {total_assigned}/{len(products)} products have collections")
    
    if failed_assignments == 0:
        print(f"\n🎉 ALL REMAINING PRODUCTS SUCCESSFULLY ASSIGNED!")
    else:
        print(f"\n⚠️  {failed_assignments} assignments failed - may need retry")
    
    return {
        'already_assigned': already_assigned,
        'drivaksel_assigned': drivaksel_assigned,
        'mellomaksel_assigned': mellomaksel_assigned,
        'failed': failed_assignments,
        'total_with_collections': total_assigned
    }

if __name__ == "__main__":
    result = main()
    print(f"\n📊 FINAL SUMMARY:")
    print(json.dumps(result, indent=2))
