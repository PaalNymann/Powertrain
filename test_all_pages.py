#!/usr/bin/env python3
"""
Test to fetch all pages from Shopify API
"""

import requests
import os
from dotenv import load_dotenv

load_dotenv()

def test_all_pages():
    """Test all pages from Shopify API"""
    
    SHOPIFY_DOMAIN = os.getenv("SHOPIFY_DOMAIN")
    SHOPIFY_TOKEN = os.getenv("SHOPIFY_TOKEN")
    
    headers = {
        "X-Shopify-Access-Token": SHOPIFY_TOKEN,
        "Content-Type": "application/json"
    }
    
    print("🔍 TESTING ALL SHOPIFY PAGES")
    print("=" * 50)
    
    url = f"https://{SHOPIFY_DOMAIN}/admin/api/2023-10/products.json?limit=250"
    page_info = None
    page_count = 0
    total_products = 0
    
    while True:
        page_count += 1
        current_url = url
        if page_info:
            current_url += f"&page_info={page_info}"
        
        print(f"📥 Page {page_count}: {current_url}")
        
        try:
            response = requests.get(current_url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                products = data.get("products", [])
                
                print(f"   ✅ Found {len(products)} products")
                total_products += len(products)
                
                # Check Link header
                link_header = response.headers.get("link", "")
                print(f"   🔗 Link: {link_header}")
                
                if 'rel="next"' in link_header:
                    # Find the next page_info specifically
                    next_link = [link for link in link_header.split(',') if 'rel="next"' in link]
                    if next_link:
                        page_info = next_link[0].split("page_info=")[1].split(">")[0]
                        print(f"   ➡️  Next page_info: {page_info}")
                    else:
                        print(f"   ❌ Could not find next page_info")
                        break
                else:
                    print(f"   ✅ No more pages")
                    break
                    
            else:
                print(f"   ❌ Error: {response.status_code}")
                break
                
        except Exception as e:
            print(f"   ❌ Exception: {e}")
            break
    
    print(f"\n📊 SUMMARY:")
    print(f"   Total pages: {page_count}")
    print(f"   Total products: {total_products}")
    print(f"   Average per page: {total_products/page_count:.1f}")

if __name__ == "__main__":
    test_all_pages() 