#!/usr/bin/env python3
"""
Direct test of Shopify API to verify product count and pagination
"""

import requests
import os
from dotenv import load_dotenv

load_dotenv()

def test_shopify_direct():
    """Test Shopify API directly"""
    
    SHOPIFY_DOMAIN = os.getenv("SHOPIFY_DOMAIN")
    SHOPIFY_TOKEN = os.getenv("SHOPIFY_TOKEN")
    
    if not all([SHOPIFY_DOMAIN, SHOPIFY_TOKEN]):
        print("❌ Missing Shopify credentials")
        return
    
    headers = {
        "X-Shopify-Access-Token": SHOPIFY_TOKEN,
        "Content-Type": "application/json"
    }
    
    print("🔍 DIRECT SHOPIFY API TEST")
    print("=" * 50)
    print(f"Domain: {SHOPIFY_DOMAIN}")
    
    # Test first page
    url = f"https://{SHOPIFY_DOMAIN}/admin/api/2023-10/products.json?limit=250"
    
    print(f"\n📥 Testing: {url}")
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        
        print(f"Status: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            products = data.get("products", [])
            
            print(f"✅ Products found: {len(products)}")
            print(f"Response keys: {list(data.keys())}")
            
            # Check Link header
            link_header = response.headers.get("link", "")
            print(f"Link header: '{link_header}'")
            
            if 'rel="next"' in link_header:
                print("✅ More pages available!")
                
                # Extract page_info
                page_info = link_header.split("page_info=")[1].split(">")[0]
                print(f"Next page_info: {page_info}")
                
                # Test second page
                next_url = f"{url}&page_info={page_info}"
                print(f"\n📥 Testing second page: {next_url}")
                
                response2 = requests.get(next_url, headers=headers, timeout=30)
                print(f"Status: {response2.status_code}")
                
                if response2.status_code == 200:
                    data2 = response2.json()
                    products2 = data2.get("products", [])
                    
                    print(f"✅ Second page products: {len(products2)}")
                    print(f"Total products: {len(products) + len(products2)}")
                    
                    link_header2 = response2.headers.get("link", "")
                    print(f"Second page Link header: '{link_header2}'")
                    
                    if 'rel="next"' in link_header2:
                        print("✅ Even more pages available!")
                    else:
                        print("✅ No more pages after second page")
                else:
                    print(f"❌ Second page failed: {response2.text}")
            else:
                print("✅ Only one page available")
                
        else:
            print(f"❌ Failed: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_shopify_direct() 