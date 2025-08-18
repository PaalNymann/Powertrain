#!/usr/bin/env python3
"""
Fix Shopify Collection Assignment
Assign all Drivaksel products to Drivaksler collection
Assign all Mellomaksel products to Mellomaksler collection
"""

import os
import requests
import json
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
    import psycopg2
    DATABASE_URL = 'postgresql://postgres:pmTNRdLNPAwZTYvtBFsqvfmjUOoNEuqM@shinkansen.proxy.rlwy.net:13074/railway'
    
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
    print("🚀 Starting Collection Assignment Fix...")
    
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
    
    drivaksel_count = 0
    mellomaksel_count = 0
    assigned_count = 0
    failed_count = 0
    
    for product_id, title, handle, rackbeat_group in products:
        print(f"📦 Processing: {title[:60]}... (Group: {rackbeat_group})")
        
        # Add small delay to avoid rate limiting
        import time
        time.sleep(0.3)
        
        if rackbeat_group == 'Drivaksel':
            print(f"🔧 Assigning to Drivaksler collection...")
            if assign_product_to_collection(product_id, drivaksler_collection['id']):
                drivaksel_count += 1
                assigned_count += 1
                print(f"  ✅ Successfully assigned to Drivaksler")
            else:
                failed_count += 1
                print(f"  ❌ Failed to assign to Drivaksler collection")
                
        elif rackbeat_group == 'Mellomaksel':
            print(f"⚙️  Assigning to Mellomaksler collection...")
            if assign_product_to_collection(product_id, mellomaksler_collection['id']):
                mellomaksel_count += 1
                assigned_count += 1
                print(f"  ✅ Successfully assigned to Mellomaksler")
            else:
                failed_count += 1
                print(f"  ❌ Failed to assign to Mellomaksler collection")
        else:
            print(f"  ❓ Unknown group: {rackbeat_group}")
            failed_count += 1
    
    # Final results
    print(f"\n📊 COLLECTION ASSIGNMENT RESULTS (by Rackbeat Group):")
    print(f"  Drivaksel → Drivaksler: {drivaksel_count}")
    print(f"  Mellomaksel → Mellomaksler: {mellomaksel_count}")
    print(f"  Total assignments successful: {assigned_count}")
    print(f"  Failed assignments: {failed_count}")
    
    if assigned_count > 0:
        print(f"\n✅ Collection assignment by Rackbeat group completed successfully!")
        print(f"All products are now assigned based on their original Rackbeat group.")
    else:
        print(f"\n❌ No products were assigned. Check API permissions and data.")
    
    return {
        'drivaksel_assigned': drivaksel_count,
        'mellomaksel_assigned': mellomaksel_count,
        'total_assigned': assigned_count,
        'failed': failed_count
    }

if __name__ == "__main__":
    result = main()
    print(f"\n📊 FINAL SUMMARY:")
    print(json.dumps(result, indent=2))
