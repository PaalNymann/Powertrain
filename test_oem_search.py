#!/usr/bin/env python3
"""
Test OEM search with real data
"""

import requests
import json

def test_oem_search():
    """Test OEM search with various OEM numbers"""
    
    railway_url = "https://web-production-0809b.up.railway.app"
    
    print("🔍 TESTING OEM SEARCH")
    print("=" * 50)
    
    # Test with some common OEM patterns
    test_oems = [
        "1510",  # Short OEM
        "1510SPORTA",  # Longer OEM
        "BMW",  # Brand name
        "OPPHE",  # Partial brand
        "TOYOTA",  # Another brand
        "203001146000",  # Long OEM number
        "100813",  # Another OEM
        "201501116000"  # Another OEM
    ]
    
    for oem in test_oems:
        print(f"\n🔍 Testing OEM: {oem}")
        
        try:
            response = requests.get(f"{railway_url}/api/part_number_search?part_number={oem}", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                count = data.get('count', 0)
                products = data.get('products', [])
                
                print(f"   ✅ Found {count} products")
                
                if count > 0:
                    print(f"   📦 Sample products:")
                    for i, product in enumerate(products[:3]):  # Show first 3
                        print(f"      {i+1}. {product.get('title', 'N/A')} (SKU: {product.get('sku', 'N/A')})")
                        if 'metafield_key' in product:
                            print(f"         Matched on: {product.get('metafield_key')} = {product.get('metafield_value')}")
                else:
                    print(f"   ❌ No products found")
            else:
                print(f"   ❌ Error: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Exception: {e}")

def test_vehicle_lookup():
    """Test vehicle lookup functionality"""
    
    railway_url = "https://web-production-0809b.up.railway.app"
    
    print("\n🚗 TESTING VEHICLE LOOKUP")
    print("=" * 50)
    
    # Test with a sample registration number
    regnr = "KH66644"  # Sample regnr
    
    print(f"🔍 Testing registration: {regnr}")
    
    try:
        response = requests.get(f"{railway_url}/api/statens_vegvesen?regnr={regnr}", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Vehicle lookup successful")
            print(f"   📋 Response: {json.dumps(data, indent=2)}")
        else:
            print(f"   ❌ Error: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"   ❌ Exception: {e}")

def test_complete_workflow():
    """Test complete workflow: regnr → vehicle → OEM → products"""
    
    railway_url = "https://web-production-0809b.up.railway.app"
    
    print("\n🔄 TESTING COMPLETE WORKFLOW")
    print("=" * 50)
    
    regnr = "KH66644"
    
    print(f"🔍 Testing complete workflow for: {regnr}")
    
    try:
        response = requests.get(f"{railway_url}/api/car_parts_search?regnr={regnr}", timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Complete workflow successful")
            print(f"   📋 Response: {json.dumps(data, indent=2)}")
        else:
            print(f"   ❌ Error: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"   ❌ Exception: {e}")

if __name__ == "__main__":
    print("🚀 COMPREHENSIVE API TESTING")
    print("=" * 50)
    
    # Test OEM search
    test_oem_search()
    
    # Test vehicle lookup
    test_vehicle_lookup()
    
    # Test complete workflow
    test_complete_workflow()
    
    print("\n" + "=" * 50)
    print("🎯 TESTING COMPLETED!") 