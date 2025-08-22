#!/usr/bin/env python3
"""
Production script to check actual MA18002 data in Rackbeat
This needs to run on Railway where requests module is available
"""

# This script should be deployed to Railway and run there
# to check the actual MA18002 product data from Rackbeat API

print("🔍 PRODUCTION SCRIPT TO CHECK MA18002 IN RACKBEAT")
print("=" * 60)
print()
print("📋 INSTRUCTIONS FOR RAILWAY DEPLOYMENT:")
print("1. Deploy this script to Railway")
print("2. Run it to check actual MA18002 data")
print("3. Compare with expected format")
print()
print("🎯 EXPECTED FINDINGS:")
print("- MA18002 should exist in Rackbeat")
print("- Group should be 'Mellomaksel'")
print("- Stock should be > 0")
print("- Price should be > 0")
print("- i_nettbutikk field should exist and = 'ja'")
print()
print("❌ IF MA18002 IS MISSING FROM SYNC:")
print("- Check if i_nettbutikk field exists")
print("- Check if value is exactly 'ja'")
print("- Check if group is exactly 'Mellomaksel'")
print("- Check stock and price values")

# Template for Railway deployment:
RAILWAY_CODE = '''
import requests
import json

def check_ma18002_in_rackbeat():
    """Check actual MA18002 data in Rackbeat API"""
    
    headers = {
        'Authorization': 'Bearer YOUR_RACKBEAT_TOKEN_HERE'
    }
    
    # Search for MA18002 specifically
    url = "https://app.rackbeat.com/api/products"
    params = {"search": "MA18002"}
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        data = response.json()
        products = data.get('data', [])
        
        for product in products:
            if product.get('number') == 'MA18002':
                print(f"✅ FOUND MA18002!")
                print(f"Name: {product.get('name')}")
                print(f"Group: {product.get('group', {}).get('name')}")
                print(f"Stock: {product.get('available_quantity')}")
                print(f"Price: {product.get('sales_price')}")
                print(f"Metadata:")
                
                for item in product.get('metadata', []):
                    slug = item.get('slug')
                    value = item.get('value')
                    print(f"  {slug}: {value}")
                
                return product
        
        print(f"❌ MA18002 NOT FOUND in {len(products)} products")
    else:
        print(f"❌ API Error: {response.status_code}")
    
    return None

if __name__ == '__main__':
    check_ma18002_in_rackbeat()
'''

print()
print("📄 RAILWAY DEPLOYMENT CODE:")
print(RAILWAY_CODE)
