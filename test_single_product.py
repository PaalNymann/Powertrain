#!/usr/bin/env python3
import os
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SHOP_DOMAIN = os.getenv("SHOPIFY_DOMAIN", "bm0did-zc.myshopify.com")
SHOP_TOKEN = os.getenv("SHOPIFY_TOKEN", "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")
RACKBEAT_API_KEY = os.getenv("RACKBEAT_API_KEY")

# Headers
HEAD_SHOP = {
    "X-Shopify-Access-Token": SHOP_TOKEN,
    "Content-Type": "application/json"
}

HEAD_RACK = {
    "Authorization": f"Bearer {RACKBEAT_API_KEY}",
    "Content-Type": "application/json"
}

def test_single_product():
    """Test creating a single product with metafields"""
    print("🧪 Testing single product creation...")
    
    # Create a test product
    test_product = {
        "product": {
            "title": "Test Product",
            "status": "active",
            "variants": [{
                "sku": "TEST123",
                "price": "99.99"
            }],
            "handle": "test-product"
        }
    }
    
    try:
        # Create product
        response = requests.post(
            f"https://{SHOP_DOMAIN}/admin/api/2023-10/products.json",
            headers=HEAD_SHOP,
            json=test_product,
            timeout=30
        )
        
        print(f"Product creation response: {response.status_code}")
        print(f"Response text: {response.text}")
        
        if response.status_code == 201:
            product_data = response.json()["product"]
            product_id = product_data["id"]
            print(f"✅ Created product with ID: {product_id}")
            
            # Test metafield creation
            test_metafield = {
                "metafield": {
                    "namespace": "custom",
                    "key": "test_field",
                    "type": "single_line_text_field",
                    "value": "test value"
                }
            }
            
            mf_response = requests.post(
                f"https://{SHOP_DOMAIN}/admin/api/2023-10/metafields.json",
                headers=HEAD_SHOP,
                json=test_metafield,
                timeout=30
            )
            
            print(f"Metafield creation response: {mf_response.status_code}")
            print(f"Metafield response text: {mf_response.text}")
            
            if mf_response.status_code == 201:
                print("✅ Metafield created successfully")
            else:
                print("❌ Metafield creation failed")
                
        else:
            print("❌ Product creation failed")
            
    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    test_single_product() 