#!/usr/bin/env python3
"""
Shopify Bulk Operations API for deleting all products
"""

import os
import requests
import time
import json
from dotenv import load_dotenv

load_dotenv()

SHOP_DOMAIN = os.getenv("SHOPIFY_DOMAIN")
SHOP_TOKEN = os.getenv("SHOPIFY_TOKEN")

HEADERS = {
    "X-Shopify-Access-Token": SHOP_TOKEN,
    "Content-Type": "application/json"
}

def create_bulk_operation():
    """Create a bulk operation to delete all products"""
    print("🔄 Creating bulk operation...")
    
    # GraphQL endpoint
    graphql_url = f"https://{SHOP_DOMAIN}/admin/api/2023-10/graphql.json"
    
    # Mutation to create bulk operation
    query_string = """
    {
      products {
        edges {
          node {
            id
          }
        }
      }
    }
    """
    
    mutation = f"""
    mutation {{
      bulkOperationRunQuery(
        query: "{query_string}"
      ) {{
        bulkOperation {{
          id
          status
        }}
        userErrors {{
          field
          message
        }}
      }}
    }}
    """
    
    response = requests.post(graphql_url, headers=HEADERS, json={"query": mutation}, timeout=30)
    
    if response.status_code != 200:
        print(f"❌ GraphQL error: {response.status_code}")
        print(f"Response: {response.text}")
        return None
    
    data = response.json()
    print(f"Bulk operation response: {json.dumps(data, indent=2)}")
    
    if "data" in data and "bulkOperationRunQuery" in data["data"]:
        bulk_op = data["data"]["bulkOperationRunQuery"]["bulkOperation"]
        return bulk_op["id"]
    
    return None

def check_bulk_operation_status(bulk_op_id):
    """Check the status of a bulk operation"""
    graphql_url = f"https://{SHOP_DOMAIN}/admin/api/2023-10/graphql.json"
    
    query = f"""
    query {{
      node(id: "{bulk_op_id}") {{
        ... on BulkOperation {{
          id
          status
          errorCode
          createdAt
          completedAt
          objectCount
          fileSize
          url
        }}
      }}
    }}
    """
    
    response = requests.post(graphql_url, headers=HEADERS, json={"query": query}, timeout=30)
    
    if response.status_code == 200:
        data = response.json()
        if "data" in data and "node" in data["data"]:
            return data["data"]["node"]
    
    return None

def delete_products_bulk():
    """Delete all products using bulk operations"""
    print("🗑️ BULK DELETE ALL PRODUCTS")
    print("=" * 30)
    
    # Step 1: Create bulk operation
    bulk_op_id = create_bulk_operation()
    
    if not bulk_op_id:
        print("❌ Failed to create bulk operation")
        return
    
    print(f"📋 Bulk operation ID: {bulk_op_id}")
    
    # Step 2: Wait for bulk operation to complete
    print("⏳ Waiting for bulk operation to complete...")
    
    while True:
        status = check_bulk_operation_status(bulk_op_id)
        
        if not status:
            print("❌ Failed to check bulk operation status")
            return
        
        print(f"Status: {status['status']}")
        
        if status['status'] == 'COMPLETED':
            print("✅ Bulk operation completed!")
            print(f"Object count: {status.get('objectCount', 'N/A')}")
            print(f"File URL: {status.get('url', 'N/A')}")
            break
        elif status['status'] == 'FAILED':
            print(f"❌ Bulk operation failed: {status.get('errorCode', 'Unknown error')}")
            return
        
        time.sleep(5)
    
    # Step 3: Download the file and delete products
    if status.get('url'):
        print("📥 Downloading product list...")
        
        # Download the file
        file_response = requests.get(status['url'], timeout=60)
        
        if file_response.status_code == 200:
            # Parse the file and extract product IDs
            lines = file_response.text.strip().split('\n')
            product_ids = []
            
            for line in lines:
                if line.strip():
                    try:
                        data = json.loads(line)
                        if 'id' in data:
                            product_ids.append(data['id'])
                    except:
                        continue
            
            print(f"📋 Found {len(product_ids)} products to delete")
            
            # Now delete them using bulk mutation
            if product_ids:
                delete_bulk_products(product_ids)
        else:
            print(f"❌ Failed to download file: {file_response.status_code}")

def delete_bulk_products(product_ids):
    """Delete products using bulk mutation"""
    print(f"🗑️ Deleting {len(product_ids)} products...")
    
    graphql_url = f"https://{SHOP_DOMAIN}/admin/api/2023-10/graphql.json"
    
    # Process in batches of 100
    batch_size = 100
    deleted_count = 0
    
    for i in range(0, len(product_ids), batch_size):
        batch = product_ids[i:i + batch_size]
        
        # Create mutation for this batch
        mutations = []
        for j, product_id in enumerate(batch):
            mutations.append(f"""
            delete{j}: productDelete(input: {{id: "{product_id}"}}) {{
                deletedProductId
                userErrors {{
                    field
                    message
                }}
            }}
            """)
        
        mutation = f"""
        mutation {{
            {''.join(mutations)}
        }}
        """
        
        print(f"Deleting batch {i//batch_size + 1}/{(len(product_ids) + batch_size - 1)//batch_size}...")
        
        response = requests.post(graphql_url, headers=HEADERS, json={"query": mutation}, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            # Count successful deletions
            batch_deleted = 0
            for key in data.get('data', {}):
                if key.startswith('delete') and data['data'][key].get('deletedProductId'):
                    batch_deleted += 1
            
            deleted_count += batch_deleted
            print(f"✅ Deleted {batch_deleted}/{len(batch)} in batch (total: {deleted_count})")
        else:
            print(f"❌ Batch deletion failed: {response.status_code}")
    
    print(f"🎉 Completed! Deleted {deleted_count} products")

if __name__ == "__main__":
    delete_products_bulk() 