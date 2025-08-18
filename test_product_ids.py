#!/usr/bin/env python3
"""
Test Product ID Format Issue
Check if Railway DB product IDs match Shopify product IDs
"""

import os
import requests
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

def get_railway_product_ids():
    """Get product IDs from Railway DB"""
    try:
        print("🔗 Getting product IDs from Railway DB...")
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        query = "SELECT id, title FROM shopify_products LIMIT 5"
        cursor.execute(query)
        products = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        print(f"✅ Railway DB product IDs (sample):")
        for product_id, title in products:
            print(f"  - ID: {product_id} (type: {type(product_id)}) - {title[:30]}...")
        
        return products
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        return []

def get_shopify_product_ids():
    """Get product IDs from Shopify API"""
    url = f"https://{SHOPIFY_DOMAIN}/admin/api/2023-10/products.json?limit=5"
    headers = get_shopify_headers()
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        products = response.json().get('products', [])
        
        print(f"✅ Shopify API product IDs (sample):")
        for product in products:
            product_id = product['id']
            title = product['title']
            print(f"  - ID: {product_id} (type: {type(product_id)}) - {title[:30]}...")
        
        return products
    else:
        print(f"❌ Failed to get Shopify products: {response.status_code}")
        return []

def test_collection_assignment(product_id, collection_id):
    """Test collection assignment with specific product ID"""
    url = f"https://{SHOPIFY_DOMAIN}/admin/api/2023-10/collects.json"
    headers = get_shopify_headers()
    
    payload = {
        "collect": {
            "product_id": product_id,
            "collection_id": collection_id
        }
    }
    
    print(f"🔗 Testing collection assignment:")
    print(f"  Product ID: {product_id} (type: {type(product_id)})")
    print(f"  Collection ID: {collection_id}")
    print(f"  Payload: {payload}")
    
    response = requests.post(url, headers=headers, json=payload)
    print(f"  Response status: {response.status_code}")
    
    if response.status_code == 201:
        print(f"  ✅ SUCCESS!")
        return True
    else:
        print(f"  ❌ FAILED: {response.text}")
        return False

def main():
    print("🚀 Testing Product ID Format Issue...")
    
    # Get product IDs from both sources
    railway_products = get_railway_product_ids()
    shopify_products = get_shopify_product_ids()
    
    if not railway_products or not shopify_products:
        print("❌ Could not get product IDs from both sources")
        return
    
    # Compare ID formats
    print(f"\n🔍 Comparing ID formats:")
    railway_id = railway_products[0][0]
    shopify_id = shopify_products[0]['id']
    
    print(f"  Railway ID: {railway_id} (type: {type(railway_id)})")
    print(f"  Shopify ID: {shopify_id} (type: {type(shopify_id)})")
    
    # Test collection assignment with Shopify ID (should work)
    print(f"\n🔗 Test 1: Collection assignment with Shopify API ID...")
    drivaksler_collection_id = 342889627797
    test_collection_assignment(shopify_id, drivaksler_collection_id)
    
    # Test collection assignment with Railway ID (might fail)
    print(f"\n🔗 Test 2: Collection assignment with Railway DB ID...")
    test_collection_assignment(railway_id, drivaksler_collection_id)
    
    # Test with converted Railway ID
    print(f"\n🔗 Test 3: Collection assignment with converted Railway ID...")
    try:
        converted_id = int(railway_id) if isinstance(railway_id, str) else railway_id
        print(f"  Converted ID: {converted_id} (type: {type(converted_id)})")
        test_collection_assignment(converted_id, drivaksler_collection_id)
    except ValueError:
        print(f"  ❌ Cannot convert Railway ID to integer: {railway_id}")

if __name__ == "__main__":
    main()
