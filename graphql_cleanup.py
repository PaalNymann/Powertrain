#!/usr/bin/env python3
"""
GraphQL bulk cleanup - Try to delete products in bulk
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

SHOP_DOMAIN = os.getenv("SHOPIFY_DOMAIN")
SHOP_TOKEN = os.getenv("SHOPIFY_TOKEN")

HEADERS = {
    "X-Shopify-Access-Token": SHOP_TOKEN,
    "Content-Type": "application/json"
}

def graphql_cleanup():
    print("🚀 GRAPHQL BULK CLEANUP")
    print("=" * 30)
    
    # GraphQL endpoint
    graphql_url = f"https://{SHOP_DOMAIN}/admin/api/2023-10/graphql.json"
    
    # First, let's try to get all product IDs
    query = """
    {
      products(first: 250) {
        edges {
          node {
            id
            title
          }
        }
        pageInfo {
          hasNextPage
          endCursor
        }
      }
    }
    """
    
    print("📥 Getting product IDs via GraphQL...")
    
    response = requests.post(graphql_url, headers=HEADERS, json={"query": query}, timeout=30)
    
    if response.status_code != 200:
        print(f"❌ GraphQL error: {response.status_code}")
        print(f"Response: {response.text[:200]}")
        return
    
    data = response.json()
    print(f"GraphQL response: {data}")
    
    # If GraphQL doesn't work, let's try a different approach
    print("\n💡 Trying alternative approach...")
    
    # Let's just use curl directly to delete products faster
    print("🔄 Using curl for faster deletion...")
    
    import subprocess
    
    # Get current count
    count_cmd = f'curl -s "https://{SHOP_DOMAIN}/admin/api/2023-10/products/count.json" -H "X-Shopify-Access-Token: {SHOP_TOKEN}"'
    result = subprocess.run(count_cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode == 0:
        import json
        count_data = json.loads(result.stdout)
        current_count = count_data["count"]
        print(f"📊 Current products: {current_count}")
        
        if current_count > 0:
            print("💥 Using curl to delete products in parallel...")
            
            # Delete products using curl in parallel
            delete_cmd = f'''
            for i in $(seq 1 10); do
                curl -s "https://{SHOP_DOMAIN}/admin/api/2023-10/products.json?limit=100" -H "X-Shopify-Access-Token: {SHOP_TOKEN}" | jq -r '.products[].id' | xargs -I {{}} curl -X DELETE "https://{SHOP_DOMAIN}/admin/api/2023-10/products/{{}}.json" -H "X-Shopify-Access-Token: {SHOP_TOKEN}" &
            done
            wait
            '''
            
            print("🚀 Running parallel deletion...")
            subprocess.run(delete_cmd, shell=True)
            
            print("✅ Parallel deletion completed!")
    else:
        print("❌ Failed to get product count")

if __name__ == "__main__":
    graphql_cleanup() 