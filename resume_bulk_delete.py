#!/usr/bin/env python3
"""
Resume bulk delete from where we left off
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

# Save the bulk operation ID from the previous run
BULK_OP_ID = "gid://shopify/BulkOperation/7229626187925"
FILE_URL = "https://storage.googleapis.com/shopify-tiers-assets-prod-us-east1/bulk-"

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

def resume_bulk_delete():
    """Resume the bulk delete process"""
    print("🔄 RESUMING BULK DELETE")
    print("=" * 25)
    
    # Check if the bulk operation is still valid
    print(f"📋 Checking bulk operation: {BULK_OP_ID}")
    status = check_bulk_operation_status(BULK_OP_ID)
    
    if not status:
        print("❌ Bulk operation not found or expired")
        print("You'll need to run the full bulk_delete.py script again")
        return
    
    print(f"Status: {status['status']}")
    
    if status['status'] != 'COMPLETED':
        print("❌ Bulk operation not completed yet")
        return
    
    print(f"✅ Bulk operation completed!")
    print(f"Object count: {status.get('objectCount', 'N/A')}")
    print(f"File URL: {status.get('url', 'N/A')}")
    
    # Download the file
    if status.get('url'):
        print("📥 Downloading product list...")
        
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
            
            # Confirm deletion
            response = input(f"Delete {len(product_ids)} products? (type 'DELETE'): ")
            if response != "DELETE":
                print("❌ Cancelled.")
                return
            
            # Now delete them using bulk mutation
            if product_ids:
                delete_bulk_products(product_ids)
        else:
            print(f"❌ Failed to download file: {file_response.status_code}")
    else:
        print("❌ No file URL available")

if __name__ == "__main__":
    resume_bulk_delete() 