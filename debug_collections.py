#!/usr/bin/env python3
"""
Debug Shopify Collections
Check what collections exist and their handles/IDs
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

def debug_collections():
    """Debug all collections in Shopify"""
    print("🔍 Checking ALL Shopify collections...")
    
    # Try both custom_collections and smart_collections
    endpoints = [
        '/admin/api/2023-10/custom_collections.json',
        '/admin/api/2023-10/smart_collections.json'
    ]
    
    all_collections = []
    
    for endpoint in endpoints:
        url = f"https://{SHOPIFY_DOMAIN}{endpoint}"
        headers = get_shopify_headers()
        
        print(f"\n📂 Checking {endpoint}...")
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            collections_key = 'custom_collections' if 'custom' in endpoint else 'smart_collections'
            collections = data.get(collections_key, [])
            
            print(f"  Found {len(collections)} collections")
            
            for collection in collections:
                print(f"    - ID: {collection['id']}, Handle: '{collection['handle']}', Title: '{collection['title']}'")
                all_collections.append(collection)
        else:
            print(f"  Error: {response.status_code} - {response.text}")
    
    print(f"\n📊 TOTAL COLLECTIONS FOUND: {len(all_collections)}")
    
    # Look for Drivaksler/Mellomaksler specifically
    drivaksler = None
    mellomaksler = None
    
    for collection in all_collections:
        handle = collection['handle'].lower()
        title = collection['title'].lower()
        
        if 'drivaks' in handle or 'drivaks' in title:
            drivaksler = collection
            print(f"🔧 FOUND DRIVAKSLER: ID={collection['id']}, Handle='{collection['handle']}', Title='{collection['title']}'")
        
        if 'mellomaks' in handle or 'mellomaks' in title:
            mellomaksler = collection
            print(f"⚙️  FOUND MELLOMAKSLER: ID={collection['id']}, Handle='{collection['handle']}', Title='{collection['title']}'")
    
    if not drivaksler:
        print("❌ DRIVAKSLER collection not found!")
    if not mellomaksler:
        print("❌ MELLOMAKSLER collection not found!")
    
    return drivaksler, mellomaksler, all_collections

if __name__ == "__main__":
    drivaksler, mellomaksler, all_collections = debug_collections()
    
    print(f"\n🎯 SUMMARY:")
    print(f"  Drivaksler found: {'✅' if drivaksler else '❌'}")
    print(f"  Mellomaksler found: {'✅' if mellomaksler else '❌'}")
    print(f"  Total collections: {len(all_collections)}")
