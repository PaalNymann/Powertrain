#!/usr/bin/env python3
"""
Debug script to investigate why MA18002 is not matched for ZT41818
Tests OEM matching between TecDoc and Shopify database
"""

import requests
import json

def test_ma18002_oems():
    """Test what OEM numbers MA18002 has in Shopify"""
    print("🔍 TESTING MA18002 OEM NUMBERS IN SHOPIFY")
    print("=" * 50)
    
    # Get MA18002 from Shopify
    url = "https://web-production-0809b.up.railway.app/api/part_number_search?part_number=MA18002"
    
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ MA18002 found in Shopify:")
            print(f"   Title: {data['products'][0]['title']}")
            print(f"   SKU: {data['products'][0]['sku']}")
            print(f"   ID: {data['products'][0]['id']}")
            
            # Now we need to get the metafields for this product
            # Since we can't access metafields directly, let's check what OEMs TecDoc returns
            return data['products'][0]['id']
        else:
            print(f"❌ Failed to get MA18002: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Error getting MA18002: {e}")
        return None

def test_zt41818_tecdoc_oems():
    """Test what OEM numbers TecDoc returns for ZT41818"""
    print("\n🔍 TESTING TECDOC OEM NUMBERS FOR ZT41818")
    print("=" * 50)
    
    # Get TecDoc OEMs for ZT41818
    url = "https://web-production-0809b.up.railway.app/api/car_parts_search"
    payload = {"license_plate": "ZT41818"}
    
    try:
        response = requests.post(url, json=payload, timeout=60)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ TecDoc search result for ZT41818:")
            print(f"   Available OEMs: {data.get('available_oems', 0)}")
            print(f"   Compatible OEMs: {data.get('compatible_oems', 0)}")
            print(f"   Vehicle: {data.get('vehicle_info', {}).get('make', 'N/A')} {data.get('vehicle_info', {}).get('model', 'N/A')} {data.get('vehicle_info', {}).get('year', 'N/A')}")
            
            # The issue is that we can't see the actual OEM numbers from this endpoint
            # We need to check if the customer-verified OEMs are being searched
            return data
        else:
            print(f"❌ Failed to get ZT41818 TecDoc data: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error getting ZT41818 TecDoc data: {e}")
        return None

def test_customer_verified_oems():
    """Test if customer-verified OEMs work in part search"""
    print("\n🔍 TESTING CUSTOMER-VERIFIED OEM NUMBERS")
    print("=" * 50)
    
    # Customer said MA18002 has these OEMs for Nissan X-Trail
    customer_oems = [
        "37000-8H310",
        "37000-8H510", 
        "37000-8H800",
        "370008H310",   # Without dashes
        "370008H510",   # Without dashes
        "370008H800"    # Without dashes
    ]
    
    for oem in customer_oems:
        print(f"\n🔍 Testing OEM: {oem}")
        url = f"https://web-production-0809b.up.railway.app/api/part_number_search?part_number={oem}"
        
        try:
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                data = response.json()
                if data.get('count', 0) > 0:
                    print(f"   ✅ Found {data['count']} products for OEM {oem}")
                    for product in data.get('products', []):
                        print(f"      - {product.get('title', 'N/A')} (SKU: {product.get('sku', 'N/A')})")
                else:
                    print(f"   ❌ No products found for OEM {oem}")
            else:
                print(f"   ❌ API error for OEM {oem}: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Exception testing OEM {oem}: {e}")

def main():
    """Main debug function"""
    print("🚨 MA18002 OEM MATCHING DEBUG")
    print("=" * 60)
    print("This script investigates why MA18002 is not found for ZT41818")
    print("=" * 60)
    
    # Test 1: Check MA18002 in Shopify
    ma18002_id = test_ma18002_oems()
    
    # Test 2: Check TecDoc OEMs for ZT41818
    zt41818_data = test_zt41818_tecdoc_oems()
    
    # Test 3: Test customer-verified OEMs directly
    test_customer_verified_oems()
    
    print("\n🎯 SUMMARY")
    print("=" * 50)
    if ma18002_id:
        print("✅ MA18002 exists in Shopify database")
    else:
        print("❌ MA18002 not found in Shopify database")
        
    if zt41818_data:
        available_oems = zt41818_data.get('available_oems', 0)
        compatible_oems = zt41818_data.get('compatible_oems', 0)
        print(f"📊 ZT41818 TecDoc search: {available_oems} available OEMs, {compatible_oems} compatible")
        
        if available_oems > 0 and compatible_oems == 0:
            print("🚨 ROOT CAUSE: TecDoc finds OEMs but none match Shopify products")
            print("   This suggests OEM format mismatch or missing metafields")
    else:
        print("❌ ZT41818 TecDoc search failed")
    
    print("\n💡 NEXT STEPS:")
    print("1. Check if MA18002 has correct Original_nummer metafields")
    print("2. Verify OEM format matching between TecDoc and Shopify")
    print("3. Test direct OEM search with customer-verified numbers")

if __name__ == "__main__":
    main()
