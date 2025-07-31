#!/usr/bin/env python3
"""
Cleanup script to remove products from Shopify that don't meet filtering criteria
Only products with available_quantity > 0 and sales_price > 0 should remain
"""

import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

# Configuration
SHOP_DOMAIN = os.getenv("SHOPIFY_DOMAIN")
SHOP_TOKEN = os.getenv("SHOPIFY_TOKEN")

HEADERS = {
    "X-Shopify-Access-Token": SHOP_TOKEN,
    "Content-Type": "application/json"
}

def get_all_shopify_products():
    """Get all products from Shopify"""
    all_products = []
    page_info = None
    
    print("📥 Fetching all Shopify products...")
    
    while True:
        url = f"https://{SHOP_DOMAIN}/admin/api/2023-10/products.json?limit=250"
        if page_info:
            url += f"&page_info={page_info}"
        
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        products = data["products"]
        all_products.extend(products)
        
        print(f"   Fetched {len(products)} products (total: {len(all_products)})")
        
        # Check for pagination
        link = response.headers.get("link", "")
        if 'rel="next"' in link:
            page_info = link.split("page_info=")[1].split(">")[0]
        else:
            break
    
    return all_products

def check_product_criteria(product):
    """Check if product meets the filtering criteria"""
    try:
        # Get the first variant
        variant = product["variants"][0]
        
        # Check if product has price and inventory
        price = float(variant.get("price", 0))
        inventory_quantity = variant.get("inventory_quantity", 0)
        
        # Criteria: price > 0 and inventory > 0
        meets_criteria = price > 0 and inventory_quantity > 0
        
        return {
            "id": product["id"],
            "title": product["title"],
            "sku": variant.get("sku", ""),
            "price": price,
            "inventory": inventory_quantity,
            "meets_criteria": meets_criteria,
            "status": product.get("status", "active")
        }
    except Exception as e:
        print(f"Error checking product {product.get('id', 'unknown')}: {e}")
        return None

def delete_product(product_id):
    """Delete a product from Shopify"""
    url = f"https://{SHOP_DOMAIN}/admin/api/2023-10/products/{product_id}.json"
    response = requests.delete(url, headers=HEADERS, timeout=30)
    return response.status_code == 200

def main():
    print("🧹 SHOPIFY CLEANUP SCRIPT")
    print("=" * 50)
    
    # Get all products
    products = get_all_shopify_products()
    print(f"\n📊 Total products in Shopify: {len(products)}")
    
    # Check each product
    print("\n🔍 Checking product criteria...")
    valid_products = []
    invalid_products = []
    
    for product in products:
        result = check_product_criteria(product)
        if result:
            if result["meets_criteria"]:
                valid_products.append(result)
            else:
                invalid_products.append(result)
    
    print(f"\n📈 ANALYSIS:")
    print(f"   ✅ Valid products (price > 0, inventory > 0): {len(valid_products)}")
    print(f"   ❌ Invalid products (to be removed): {len(invalid_products)}")
    
    if invalid_products:
        print(f"\n🗑️  PRODUCTS TO REMOVE:")
        for product in invalid_products[:10]:  # Show first 10
            print(f"   - {product['title']} (SKU: {product['sku']}, Price: {product['price']}, Inventory: {product['inventory']})")
        
        if len(invalid_products) > 10:
            print(f"   ... and {len(invalid_products) - 10} more")
        
        # Ask for confirmation
        response = input(f"\n⚠️  Do you want to DELETE {len(invalid_products)} invalid products? (yes/no): ")
        
        if response.lower() == "yes":
            print(f"\n🗑️  Deleting {len(invalid_products)} invalid products...")
            deleted_count = 0
            
            for product in invalid_products:
                if delete_product(product["id"]):
                    deleted_count += 1
                    print(f"   ✅ Deleted: {product['title']}")
                else:
                    print(f"   ❌ Failed to delete: {product['title']}")
            
            print(f"\n🎉 Cleanup complete! Deleted {deleted_count} products.")
            print(f"   Remaining products: {len(valid_products)}")
        else:
            print("❌ Cleanup cancelled.")
    else:
        print("\n✅ No cleanup needed! All products meet the criteria.")

if __name__ == "__main__":
    main() 