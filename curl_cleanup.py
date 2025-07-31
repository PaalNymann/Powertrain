#!/usr/bin/env python3
"""
Curl cleanup - Fast deletion using curl and parallel processing
"""

import os
import subprocess
import json
from dotenv import load_dotenv

load_dotenv()

SHOP_DOMAIN = os.getenv("SHOPIFY_DOMAIN")
SHOP_TOKEN = os.getenv("SHOPIFY_TOKEN")

def curl_cleanup():
    print("⚡ CURL CLEANUP - FAST DELETION")
    print("=" * 35)
    
    # Get current count
    count_cmd = f'curl -s "https://{SHOP_DOMAIN}/admin/api/2023-10/products/count.json" -H "X-Shopify-Access-Token: {SHOP_TOKEN}"'
    result = subprocess.run(count_cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode != 0:
        print("❌ Failed to get product count")
        return
    
    count_data = json.loads(result.stdout)
    current_count = count_data["count"]
    
    print(f"📊 Products to delete: {current_count}")
    
    if current_count == 0:
        print("✅ No products to delete!")
        return
    
    # Confirm
    response = input(f"Delete all {current_count} products? (type 'DELETE'): ")
    if response != "DELETE":
        print("❌ Cancelled.")
        return
    
    print("⚡ Starting fast deletion with curl...")
    
    # Create a bash script for parallel deletion
    script = f'''#!/bin/bash
echo "🚀 Starting parallel deletion..."

# Function to delete products
delete_products() {{
    local batch=$1
    echo "Batch $batch: Starting deletion..."
    
    # Get products and delete them
    curl -s "https://{SHOP_DOMAIN}/admin/api/2023-10/products.json?limit=100" \\
         -H "X-Shopify-Access-Token: {SHOP_TOKEN}" \\
         | jq -r '.products[].id' \\
         | xargs -I {{}} curl -X DELETE "https://{SHOP_DOMAIN}/admin/api/2023-10/products/{{}}.json" \\
         -H "X-Shopify-Access-Token: {SHOP_TOKEN}" \\
         -s > /dev/null
    
    echo "Batch $batch: Completed"
}}

# Run multiple batches in parallel
for i in $(seq 1 5); do
    delete_products $i &
done

# Wait for all to complete
wait

echo "✅ Parallel deletion completed!"
'''
    
    # Write script to file
    with open('delete_script.sh', 'w') as f:
        f.write(script)
    
    # Make it executable and run
    subprocess.run('chmod +x delete_script.sh', shell=True)
    
    print("🚀 Running parallel deletion script...")
    subprocess.run('./delete_script.sh', shell=True)
    
    # Clean up
    subprocess.run('rm delete_script.sh', shell=True)
    
    # Final check
    result = subprocess.run(count_cmd, shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        final_count = json.loads(result.stdout)["count"]
        print(f"\n🎉 CLEANUP COMPLETE!")
        print(f"📊 Remaining products: {final_count}")
        
        if final_count == 0:
            print("✅ All products deleted!")
        else:
            print(f"⚠️  {final_count} products still remain.")

if __name__ == "__main__":
    curl_cleanup() 