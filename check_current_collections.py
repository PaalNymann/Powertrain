#!/usr/bin/env python3
"""
Check Current Collection Assignments
See which products are actually assigned to which collections
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

def get_products_with_groups():
    """Get all products from Railway DB with their groups"""
    try:
        print("🔗 Connecting to Railway PostgreSQL...")
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        query = """
        SELECT sp.id, sp.title, pm_group.value as rackbeat_group
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
        
        return products
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        return []

def get_shopify_collections():
    """Get Shopify collections"""
    url = f"https://{SHOPIFY_DOMAIN}/admin/api/2023-10/custom_collections.json"
    headers = get_shopify_headers()
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        collections = response.json().get('custom_collections', [])
        
        collection_map = {}
        for collection in collections:
            handle = collection['handle'].lower()
            title = collection['title'].lower()
            if 'drivaksler' in handle or 'drivaksler' in title:
                collection_map['Drivaksel'] = collection
            elif 'mellomaksler' in handle or 'mellomaksler' in title:
                collection_map['Mellomaksel'] = collection
        
        return collection_map
    return {}

def check_product_collections(product_id):
    """Check which collections a product belongs to"""
    url = f"https://{SHOPIFY_DOMAIN}/admin/api/2023-10/collects.json"
    headers = get_shopify_headers()
    params = {'product_id': product_id}
    
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json().get('collects', [])
    return []

def main():
    print("🔍 Checking Current Collection Assignments...")
    
    # Get collections
    print("\n📂 Getting Shopify collections...")
    collections = get_shopify_collections()
    
    if not collections:
        print("❌ Could not find target collections!")
        return
    
    print(f"✅ Found collections:")
    for group, collection in collections.items():
        print(f"  - {group} → {collection['title']} (ID: {collection['id']})")
    
    # Get products
    print(f"\n📦 Getting products from Railway DB...")
    products = get_products_with_groups()
    print(f"✅ Found {len(products)} products")
    
    # Check assignments
    print(f"\n🔍 Checking current collection assignments...")
    
    correctly_assigned = 0
    incorrectly_assigned = 0
    not_assigned = 0
    
    drivaksel_correct = 0
    mellomaksel_correct = 0
    
    for i, (product_id, title, rackbeat_group) in enumerate(products):
        if i % 20 == 0:
            print(f"  Progress: {i+1}/{len(products)}")
        
        # Check current collections
        current_collects = check_product_collections(product_id)
        
        target_collection = collections.get(rackbeat_group)
        if not target_collection:
            continue
        
        # Check if assigned to correct collection
        is_correctly_assigned = any(
            collect['collection_id'] == target_collection['id'] 
            for collect in current_collects
        )
        
        if is_correctly_assigned:
            correctly_assigned += 1
            if rackbeat_group == 'Drivaksel':
                drivaksel_correct += 1
            else:
                mellomaksel_correct += 1
        elif current_collects:
            incorrectly_assigned += 1
            print(f"    ❌ WRONG: {title[:50]}... (Group: {rackbeat_group})")
            for collect in current_collects:
                print(f"        In collection: {collect['collection_id']}")
        else:
            not_assigned += 1
            print(f"    ❓ NOT ASSIGNED: {title[:50]}... (Group: {rackbeat_group})")
        
        # Small delay
        import time
        time.sleep(0.1)
    
    # Results
    print(f"\n📊 COLLECTION ASSIGNMENT STATUS:")
    print(f"  ✅ Correctly assigned: {correctly_assigned}")
    print(f"    - Drivaksel → Drivaksler: {drivaksel_correct}")
    print(f"    - Mellomaksel → Mellomaksler: {mellomaksel_correct}")
    print(f"  ❌ Incorrectly assigned: {incorrectly_assigned}")
    print(f"  ❓ Not assigned: {not_assigned}")
    print(f"  📊 Total products: {len(products)}")
    
    percentage_correct = (correctly_assigned / len(products)) * 100 if products else 0
    print(f"\n🎯 ACCURACY: {percentage_correct:.1f}% correctly assigned")
    
    if correctly_assigned == len(products):
        print(f"\n🎉 ALL PRODUCTS ARE CORRECTLY ASSIGNED!")
    elif correctly_assigned > len(products) * 0.8:
        print(f"\n👍 MOST PRODUCTS ARE CORRECTLY ASSIGNED!")
    else:
        print(f"\n⚠️  MANY PRODUCTS NEED REASSIGNMENT!")
    
    return {
        'total': len(products),
        'correctly_assigned': correctly_assigned,
        'drivaksel_correct': drivaksel_correct,
        'mellomaksel_correct': mellomaksel_correct,
        'incorrectly_assigned': incorrectly_assigned,
        'not_assigned': not_assigned,
        'accuracy_percent': percentage_correct
    }

if __name__ == "__main__":
    result = main()
    print(f"\n📊 FINAL SUMMARY:")
    print(json.dumps(result, indent=2))
