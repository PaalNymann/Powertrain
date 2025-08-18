#!/usr/bin/env python3
"""
Test Shopify API Access
Simple test to check if we can create/delete collects
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

def test_shopify_api():
    """Test basic Shopify API access"""
    print("🔍 Testing Shopify API access...")
    
    # Test 1: Get shop info
    print("\n📊 Test 1: Getting shop info...")
    url = f"https://{SHOPIFY_DOMAIN}/admin/api/2023-10/shop.json"
    headers = get_shopify_headers()
    
    response = requests.get(url, headers=headers)
    print(f"  Status: {response.status_code}")
    if response.status_code == 200:
        shop = response.json().get('shop', {})
        print(f"  Shop: {shop.get('name', 'Unknown')}")
        print(f"  ✅ Basic API access works")
    else:
        print(f"  ❌ API access failed: {response.text}")
        return
    
    # Test 2: Get collections
    print("\n📂 Test 2: Getting collections...")
    url = f"https://{SHOPIFY_DOMAIN}/admin/api/2023-10/custom_collections.json"
    response = requests.get(url, headers=headers)
    print(f"  Status: {response.status_code}")
    
    if response.status_code == 200:
        collections = response.json().get('custom_collections', [])
        print(f"  Found {len(collections)} collections")
        
        drivaksler = None
        mellomaksler = None
        
        for collection in collections:
            handle = collection['handle'].lower()
            title = collection['title'].lower()
            print(f"    - {collection['title']} (ID: {collection['id']}, Handle: {collection['handle']})")
            
            if 'drivaksler' in handle or 'drivaksler' in title:
                drivaksler = collection
            elif 'mellomaksler' in handle or 'mellomaksler' in title:
                mellomaksler = collection
        
        if drivaksler and mellomaksler:
            print(f"  ✅ Found both target collections")
            
            # Test 3: Get a sample product
            print(f"\n📦 Test 3: Getting sample product...")
            url = f"https://{SHOPIFY_DOMAIN}/admin/api/2023-10/products.json?limit=1"
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                products = response.json().get('products', [])
                if products:
                    product = products[0]
                    product_id = product['id']
                    print(f"  Sample product: {product['title'][:50]}... (ID: {product_id})")
                    
                    # Test 4: Try to create a collect
                    print(f"\n🔗 Test 4: Testing collect creation...")
                    url = f"https://{SHOPIFY_DOMAIN}/admin/api/2023-10/collects.json"
                    
                    payload = {
                        "collect": {
                            "product_id": product_id,
                            "collection_id": drivaksler['id']
                        }
                    }
                    
                    response = requests.post(url, headers=headers, json=payload)
                    print(f"  Create collect status: {response.status_code}")
                    
                    if response.status_code == 201:
                        collect_id = response.json()['collect']['id']
                        print(f"  ✅ Collect created successfully (ID: {collect_id})")
                        
                        # Test 5: Delete the test collect
                        print(f"\n🗑️  Test 5: Cleaning up test collect...")
                        delete_url = f"https://{SHOPIFY_DOMAIN}/admin/api/2023-10/collects/{collect_id}.json"
                        delete_response = requests.delete(delete_url, headers=headers)
                        print(f"  Delete collect status: {delete_response.status_code}")
                        
                        if delete_response.status_code == 200:
                            print(f"  ✅ Test collect deleted successfully")
                        else:
                            print(f"  ❌ Failed to delete test collect: {delete_response.text}")
                    
                    elif response.status_code == 422:
                        error_data = response.json()
                        print(f"  ⚠️  Collect creation failed (422): {error_data}")
                        if 'errors' in error_data:
                            for field, messages in error_data['errors'].items():
                                print(f"    - {field}: {messages}")
                    else:
                        print(f"  ❌ Collect creation failed: {response.status_code} - {response.text}")
                        
                        # Check rate limiting
                        if response.status_code == 429:
                            print(f"  🚨 RATE LIMITED! Need to slow down API calls")
                        elif response.status_code == 403:
                            print(f"  🚨 FORBIDDEN! Check API permissions")
                        elif response.status_code == 401:
                            print(f"  🚨 UNAUTHORIZED! Check API token")
                
                else:
                    print(f"  ❌ No products found for testing")
            else:
                print(f"  ❌ Failed to get products: {response.status_code}")
        else:
            print(f"  ❌ Target collections not found")
    else:
        print(f"  ❌ Failed to get collections: {response.status_code}")

if __name__ == "__main__":
    test_shopify_api()
