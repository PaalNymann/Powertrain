#!/usr/bin/env python3
"""
Simple analysis script to check Shopify products without making changes
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

# Configuration
SHOP_DOMAIN = os.getenv("SHOPIFY_DOMAIN")
SHOP_TOKEN = os.getenv("SHOPIFY_TOKEN")

HEADERS = {
    "X-Shopify-Access-Token": SHOP_TOKEN,
    "Content-Type": "application/json"
}

def analyze_shopify_products():
    """Analyze products in Shopify"""
    print("🔍 SHOPIFY PRODUCT ANALYSIS")
    print("=" * 50)
    
    # Get total count
    count_url = f"https://{SHOP_DOMAIN}/admin/api/2023-10/products/count.json"
    count_response = requests.get(count_url, headers=HEADERS, timeout=30)
    total_count = count_response.json()["count"]
    
    print(f"📊 Total products in Shopify: {total_count}")
    
    # Get first 50 products for analysis
    print(f"\n📥 Fetching first 50 products for analysis...")
    url = f"https://{SHOP_DOMAIN}/admin/api/2023-10/products.json?limit=50"
    response = requests.get(url, headers=HEADERS, timeout=30)
    products = response.json()["products"]
    
    print(f"📈 Analyzing {len(products)} sample products...")
    
    valid_count = 0
    invalid_count = 0
    zero_price_count = 0
    zero_inventory_count = 0
    both_zero_count = 0
    
    print(f"\n📋 SAMPLE PRODUCTS ANALYSIS:")
    print(f"{'Title':<40} {'SKU':<15} {'Price':<8} {'Inventory':<10} {'Status'}")
    print("-" * 90)
    
    for product in products:
        try:
            variant = product["variants"][0]
            price = float(variant.get("price", 0))
            inventory = variant.get("inventory_quantity", 0)
            sku = variant.get("sku", "N/A")
            title = product["title"][:39]  # Truncate long titles
            status = product.get("status", "active")
            
            # Count issues
            if price == 0:
                zero_price_count += 1
            if inventory == 0:
                zero_inventory_count += 1
            if price == 0 and inventory == 0:
                both_zero_count += 1
            
            # Check if valid
            if price > 0 and inventory > 0:
                valid_count += 1
                status_indicator = "✅"
            else:
                invalid_count += 1
                status_indicator = "❌"
            
            print(f"{title:<40} {sku:<15} {price:<8.2f} {inventory:<10} {status_indicator}")
            
        except Exception as e:
            print(f"Error analyzing product {product.get('id', 'unknown')}: {e}")
    
    print(f"\n📊 ANALYSIS SUMMARY:")
    print(f"   ✅ Valid products (price > 0, inventory > 0): {valid_count}")
    print(f"   ❌ Invalid products: {invalid_count}")
    print(f"   💰 Zero price products: {zero_price_count}")
    print(f"   📦 Zero inventory products: {zero_inventory_count}")
    print(f"   🚫 Both zero (price & inventory): {both_zero_count}")
    
    # Estimate total invalid products
    if len(products) > 0:
        invalid_percentage = (invalid_count / len(products)) * 100
        estimated_invalid_total = int((invalid_percentage / 100) * total_count)
        
        print(f"\n📈 ESTIMATED TOTALS (based on sample):")
        print(f"   Estimated invalid products: ~{estimated_invalid_total}")
        print(f"   Estimated valid products: ~{total_count - estimated_invalid_total}")
        print(f"   Invalid percentage: {invalid_percentage:.1f}%")
    
    print(f"\n💡 RECOMMENDATION:")
    if invalid_count > valid_count:
        print(f"   🧹 Cleanup needed! Most products don't meet criteria.")
        print(f"   Expected: ~1,670 valid products from Rackbeat")
        print(f"   Current: ~{total_count} total products (many invalid)")
    else:
        print(f"   ✅ Store looks good! Most products meet criteria.")

if __name__ == "__main__":
    analyze_shopify_products() 