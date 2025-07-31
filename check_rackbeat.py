#!/usr/bin/env python3
"""
Check Rackbeat data to see what products should be synced to Shopify
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

# Configuration
RACKBEAT_API_KEY = os.getenv("RACKBEAT_API_KEY")
RACKBEAT_ENDPOINT = os.getenv("RACKBEAT_ENDPOINT", "https://app.rackbeat.com/api/products")

HEADERS = {
    "Authorization": f"Bearer {RACKBEAT_API_KEY}",
    "Content-Type": "application/json"
}

def check_rackbeat_products():
    """Check products in Rackbeat"""
    print("🔍 RACKBEAT PRODUCT ANALYSIS")
    print("=" * 50)
    
    # Get first page to see total count
    print("📥 Fetching first page from Rackbeat...")
    url = f"{RACKBEAT_ENDPOINT}?limit=250&page=1"
    response = requests.get(url, headers=HEADERS, timeout=30)
    
    if response.status_code not in [200, 206]:  # Accept both 200 and 206 (Partial Content)
        print(f"❌ Error accessing Rackbeat API: {response.status_code}")
        print(f"Response: {response.text[:200]}")
        return
    
    data = response.json()
    products = data.get("products", [])
    total_pages = data.get("pages", 1)
    
    print(f"📊 Rackbeat API Response:")
    print(f"   Products in first page: {len(products)}")
    print(f"   Total pages: {total_pages}")
    print(f"   Estimated total products: {len(products) * total_pages}")
    
    # Analyze first page products
    print(f"\n📈 Analyzing first page products...")
    
    total_products = len(products)
    valid_products = 0
    invalid_products = 0
    zero_price_count = 0
    zero_stock_count = 0
    both_zero_count = 0
    
    print(f"\n📋 FIRST PAGE PRODUCTS ANALYSIS:")
    print(f"{'Number':<15} {'Name':<40} {'Price':<10} {'Stock':<8} {'Status'}")
    print("-" * 90)
    
    for product in products:
        try:
            number = product.get("number", "N/A")
            name = product.get("name", "N/A")[:39]  # Truncate long names
            sales_price = float(product.get("sales_price", 0))
            available_quantity = int(product.get("available_quantity", 0))
            is_barred = product.get("is_barred", False)
            
            # Count issues
            if sales_price == 0:
                zero_price_count += 1
            if available_quantity == 0:
                zero_stock_count += 1
            if sales_price == 0 and available_quantity == 0:
                both_zero_count += 1
            
            # Check if valid (meets sync criteria)
            if sales_price > 0 and available_quantity > 0 and not is_barred:
                valid_products += 1
                status_indicator = "✅"
            else:
                invalid_products += 1
                status_indicator = "❌"
            
            print(f"{number:<15} {name:<40} {sales_price:<10.2f} {available_quantity:<8} {status_indicator}")
            
        except Exception as e:
            print(f"Error analyzing product {product.get('number', 'unknown')}: {e}")
    
    print(f"\n📊 FIRST PAGE SUMMARY:")
    print(f"   ✅ Valid products (price > 0, stock > 0, not barred): {valid_products}")
    print(f"   ❌ Invalid products: {invalid_products}")
    print(f"   💰 Zero price products: {zero_price_count}")
    print(f"   📦 Zero stock products: {zero_stock_count}")
    print(f"   🚫 Both zero (price & stock): {both_zero_count}")
    
    # Estimate totals
    if total_products > 0:
        valid_percentage = (valid_products / total_products) * 100
        estimated_valid_total = int((valid_percentage / 100) * (len(products) * total_pages))
        
        print(f"\n📈 ESTIMATED TOTALS (based on first page):")
        print(f"   Estimated total products in Rackbeat: ~{len(products) * total_pages}")
        print(f"   Estimated valid products for sync: ~{estimated_valid_total}")
        print(f"   Valid percentage: {valid_percentage:.1f}%")
    
    print(f"\n💡 COMPARISON WITH SHOPIFY:")
    print(f"   Expected in Shopify: ~{estimated_valid_total} products")
    print(f"   Current in Shopify: 16,634 products")
    print(f"   Difference: +{16634 - estimated_valid_total} extra products")
    
    print(f"\n🎯 RECOMMENDATION:")
    if estimated_valid_total < 2000:
        print(f"   🧹 Cleanup needed! Shopify has {16634 - estimated_valid_total} extra products.")
        print(f"   Expected: ~{estimated_valid_total} products from Rackbeat")
        print(f"   Current: 16,634 products in Shopify")
    else:
        print(f"   ✅ Numbers look reasonable.")

if __name__ == "__main__":
    check_rackbeat_products() 