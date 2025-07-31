#!/usr/bin/env python3
import os
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SHOP_DOMAIN = os.getenv("SHOPIFY_DOMAIN", "bm0did-zc.myshopify.com")
SHOP_TOKEN = os.getenv("SHOPIFY_TOKEN", "your_shopify_token_here")

# Headers
HEAD_SHOP = {
    "X-Shopify-Access-Token": SHOP_TOKEN,
    "Content-Type": "application/json"
}

def test_metafields():
    """Test creating the specific metafields we need"""
    print("🧪 Testing specific metafields...")
    
    # Create a test product first
    test_product = {
        "product": {
            "title": "Test Product 2",
            "status": "active",
            "variants": [{
                "sku": "TEST456",
                "price": "99.99"
            }],
            "handle": "test-product-2"
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
        
        if response.status_code == 201:
            product_data = response.json()["product"]
            product_id = product_data["id"]
            print(f"✅ Created product with ID: {product_id}")
            
            # Test the specific metafields we need
            metafields = [
                {"namespace": "custom", "key": "number", "type": "single_line_text_field", "value": "TEST456"},
                {"namespace": "custom", "key": "original_nummer", "type": "single_line_text_field", "value": ""},
                {"namespace": "custom", "key": "tirsan_varenummer", "type": "single_line_text_field", "value": ""},
                {"namespace": "custom", "key": "odm_varenummer", "type": "single_line_text_field", "value": ""},
                {"namespace": "custom", "key": "ims_varenummer", "type": "single_line_text_field", "value": ""},
                {"namespace": "custom", "key": "welte_varenummer", "type": "single_line_text_field", "value": ""},
                {"namespace": "custom", "key": "bakkeren_varenummer", "type": "single_line_text_field", "value": ""}
            ]
            
            for i, mf in enumerate(metafields):
                mf["owner_id"] = product_id
                mf["owner_resource"] = "product"
                
                mf_response = requests.post(
                    f"https://{SHOP_DOMAIN}/admin/api/2023-10/metafields.json",
                    headers=HEAD_SHOP,
                    json={"metafield": mf},
                    timeout=30
                )
                
                print(f"Metafield {i+1} ({mf['key']}): {mf_response.status_code}")
                if mf_response.status_code != 201:
                    print(f"  Error: {mf_response.text}")
                else:
                    print(f"  ✅ Success")
                    
        else:
            print(f"❌ Product creation failed: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    test_metafields() 