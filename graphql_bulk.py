#!/usr/bin/env python3
"""
GraphQL bulk deletion - Try to delete products using GraphQL mutations
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

def graphql_bulk_delete():
    print("🚀 GRAPHQL BULK DELETE")
    print("=" * 30)
    
    # GraphQL endpoint
    graphql_url = f"https://{SHOP_DOMAIN}/admin/api/2023-10/graphql.json"
    
    # First, let's try to get all product IDs using GraphQL
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
    
    print("📥 Getting products via GraphQL...")
    
    response = requests.post(graphql_url, headers=HEADERS, json={"query": query}, timeout=30)
    
    if response.status_code != 200:
        print(f"❌ GraphQL error: {response.status_code}")
        print(f"Response: {response.text[:200]}")
        return
    
    data = response.json()
    print(f"GraphQL response: {data}")
    
    # If GraphQL works, let's try a bulk deletion mutation
    print("\n💡 Trying bulk deletion mutation...")
    
    # Try a bulk deletion mutation
    mutation = """
    mutation bulkDeleteProducts($productIds: [ID!]!) {
      bulkDeleteProducts(productIds: $productIds) {
        deletedProductIds
        userErrors {
          field
          message
        }
      }
    }
    """
    
    # Get some product IDs to test with
    product_ids = []
    if "data" in data and "products" in data["data"]:
        for edge in data["data"]["products"]["edges"]:
            product_ids.append(edge["node"]["id"])
    
    if product_ids:
        print(f"Testing with {len(product_ids)} products...")
        
        variables = {
            "productIds": product_ids[:10]  # Test with first 10
        }
        
        mutation_response = requests.post(
            graphql_url, 
            headers=HEADERS, 
            json={"query": mutation, "variables": variables}, 
            timeout=30
        )
        
        if mutation_response.status_code == 200:
            mutation_data = mutation_response.json()
            print(f"Mutation response: {mutation_data}")
        else:
            print(f"❌ Mutation failed: {mutation_response.status_code}")
            print(f"Response: {mutation_response.text[:200]}")
    else:
        print("❌ No products found to test with")

if __name__ == "__main__":
    graphql_bulk_delete() 