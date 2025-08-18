#!/usr/bin/env python3
"""
Basic Shopify API Test
Test if we can access Shopify API at all
"""

import os
import requests
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

def test_basic_api():
    """Test basic Shopify API access"""
    print("🔍 Testing basic Shopify API access...")
    
    # Test 1: Get shop info
    print("\n📊 Test 1: Shop info...")
    url = f"https://{SHOPIFY_DOMAIN}/admin/api/2023-10/shop.json"
    headers = get_shopify_headers()
    
    response = requests.get(url, headers=headers)
    print(f"  Status: {response.status_code}")
    
    if response.status_code == 200:
        shop = response.json().get('shop', {})
        print(f"  ✅ Shop: {shop.get('name', 'Unknown')}")
    else:
        print(f"  ❌ Failed: {response.text[:200]}")
        return False
    
    # Test 2: Get collections
    print("\n📂 Test 2: Collections...")
    url = f"https://{SHOPIFY_DOMAIN}/admin/api/2023-10/custom_collections.json?limit=5"
    response = requests.get(url, headers=headers)
    print(f"  Status: {response.status_code}")
    
    if response.status_code == 200:
        collections = response.json().get('custom_collections', [])
        print(f"  ✅ Found {len(collections)} collections")
        for collection in collections:
            print(f"    - {collection['title']} (ID: {collection['id']})")
    else:
        print(f"  ❌ Failed: {response.text[:200]}")
        return False
    
    # Test 3: Get products count
    print("\n📦 Test 3: Products count...")
    url = f"https://{SHOPIFY_DOMAIN}/admin/api/2023-10/products/count.json"
    response = requests.get(url, headers=headers)
    print(f"  Status: {response.status_code}")
    
    if response.status_code == 200:
        count = response.json().get('count', 0)
        print(f"  ✅ Products: {count}")
    else:
        print(f"  ❌ Failed: {response.text[:200]}")
        return False
    
    # Test 4: Get one product
    print("\n📦 Test 4: Get one product...")
    url = f"https://{SHOPIFY_DOMAIN}/admin/api/2023-10/products.json?limit=1"
    response = requests.get(url, headers=headers)
    print(f"  Status: {response.status_code}")
    
    if response.status_code == 200:
        products = response.json().get('products', [])
        if products:
            product = products[0]
            print(f"  ✅ Product: {product['title'][:50]}... (ID: {product['id']})")
            return product['id']
        else:
            print(f"  ❌ No products found")
            return False
    else:
        print(f"  ❌ Failed: {response.text[:200]}")
        return False

def test_collect_operations(product_id):
    """Test collect operations with a real product"""
    print(f"\n🔗 Test 5: Collect operations with product {product_id}...")
    headers = get_shopify_headers()
    
    # Get current collections for product
    url = f"https://{SHOPIFY_DOMAIN}/admin/api/2023-10/collects.json?product_id={product_id}"
    response = requests.get(url, headers=headers)
    print(f"  Get collects status: {response.status_code}")
    
    if response.status_code == 200:
        collects = response.json().get('collects', [])
        print(f"  ✅ Product has {len(collects)} collections")
        return True
    else:
        print(f"  ❌ Failed to get collects: {response.text[:200]}")
        return False

if __name__ == "__main__":
    print("🚀 Starting Basic Shopify API Test...")
    
    product_id = test_basic_api()
    
    if product_id:
        test_collect_operations(product_id)
        print(f"\n✅ Basic API access is working!")
    else:
        print(f"\n❌ Basic API access failed!")
