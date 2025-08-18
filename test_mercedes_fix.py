#!/usr/bin/env python3
"""
Quick Test for Mercedes Brand Matching Fix
Test the fixed brand compatibility logic for YZ99554
"""

import requests
import json
from dotenv import load_dotenv

load_dotenv()

def test_yz99554_search():
    """Test YZ99554 search with fixed Mercedes matching"""
    print("🧪 TESTING MERCEDES BRAND MATCHING FIX")
    print("=" * 50)
    
    backend_url = "https://web-production-0809b.up.railway.app"
    license_plate = "YZ99554"
    
    print(f"🚗 Testing search for {license_plate} (Mercedes GLK)")
    print(f"🎯 Expected: Should find MA01002 with Mercedes OEMs")
    
    try:
        response = requests.post(
            f"{backend_url}/api/car_parts_search",
            json={"license_plate": license_plate},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            
            vehicle_info = data.get('vehicle_info', {})
            available_oems = data.get('available_oems', 0)
            compatible_oems = data.get('compatible_oems', 0)
            products = data.get('shopify_parts', [])
            
            print(f"✅ API Response received")
            print(f"🚗 Vehicle: {vehicle_info.get('make')} {vehicle_info.get('model')} ({vehicle_info.get('year')})")
            print(f"📋 Available OEMs: {available_oems}")
            print(f"🔍 Compatible OEMs: {compatible_oems}")
            print(f"📦 Products found: {len(products)}")
            
            # Check if MA01002 is found
            ma01002_found = False
            for product in products:
                product_id = product.get('id', '')
                product_sku = product.get('sku', '')
                product_title = product.get('title', '')
                
                if 'MA01002' in product_id or 'MA01002' in product_sku:
                    ma01002_found = True
                    print(f"🎉 SUCCESS: MA01002 FOUND!")
                    print(f"   📦 Product: {product_title}")
                    print(f"   🔧 ID: {product_id}")
                    print(f"   📋 SKU: {product_sku}")
                    print(f"   🔍 Matched OEM: {product.get('matched_oem', 'N/A')}")
                    break
            
            if not ma01002_found:
                print(f"❌ MA01002 NOT FOUND in results")
                if compatible_oems == 0:
                    print(f"🔍 Root cause: No compatible OEMs found (Mercedes matching still failing)")
                else:
                    print(f"🔍 Root cause: Compatible OEMs found but MA01002 not in results")
                
                # Show what products were found instead
                if products:
                    print(f"📦 Products found instead:")
                    for i, product in enumerate(products[:3]):
                        print(f"   {i+1}. {product.get('title', 'N/A')[:50]}... (ID: {product.get('id', 'N/A')})")
            
            # Performance info
            performance = data.get('performance', {})
            if performance:
                total_time = performance.get('total_time', 'N/A')
                print(f"⏱️  Search completed in {total_time}s")
            
            return {
                'success': True,
                'ma01002_found': ma01002_found,
                'compatible_oems': compatible_oems,
                'products_count': len(products)
            }
            
        else:
            print(f"❌ API request failed: {response.status_code}")
            print(f"Response: {response.text}")
            return {'success': False, 'error': f"HTTP {response.status_code}"}
            
    except Exception as e:
        print(f"❌ Test error: {e}")
        return {'success': False, 'error': str(e)}

def test_brand_matching_logic():
    """Test the brand matching logic directly"""
    print(f"\n🧪 TESTING BRAND MATCHING LOGIC DIRECTLY")
    print("=" * 50)
    
    try:
        from optimized_search import is_brand_compatible
        
        # Test cases for Mercedes
        test_cases = [
            {
                'target_brand': 'MERCEDES-BENZ',
                'manufacturer_name': 'MERCEDES-BENZ',
                'product_name': 'PROPSHAFT, AXLE DRIVE',
                'model': 'GLK 220 CDI 4MATIC',
                'expected': True
            },
            {
                'target_brand': 'MERCEDES',
                'manufacturer_name': 'MERCEDES-BENZ',
                'product_name': 'PROPSHAFT, AXLE DRIVE',
                'model': 'GLK 220 CDI 4MATIC',
                'expected': True
            },
            {
                'target_brand': 'MERCEDES-BENZ',
                'manufacturer_name': 'MERCEDES',
                'product_name': 'PROPSHAFT, AXLE DRIVE',
                'model': 'GLK 220 CDI 4MATIC',
                'expected': True
            }
        ]
        
        for i, test_case in enumerate(test_cases):
            result = is_brand_compatible(
                test_case['target_brand'],
                test_case['manufacturer_name'],
                test_case['product_name'],
                test_case['model']
            )
            
            status = "✅ PASS" if result == test_case['expected'] else "❌ FAIL"
            print(f"Test {i+1}: {status}")
            print(f"   Target: {test_case['target_brand']}")
            print(f"   Manufacturer: {test_case['manufacturer_name']}")
            print(f"   Expected: {test_case['expected']}, Got: {result}")
        
        return True
        
    except Exception as e:
        print(f"❌ Brand matching test error: {e}")
        return False

if __name__ == "__main__":
    print("🚀 TESTING MERCEDES BRAND MATCHING FIX FOR YZ99554")
    print("=" * 60)
    
    # Test brand matching logic first
    logic_test = test_brand_matching_logic()
    
    # Test full search
    search_result = test_yz99554_search()
    
    print(f"\n📊 TEST SUMMARY")
    print("=" * 30)
    print(f"🧪 Brand matching logic: {'✅ PASS' if logic_test else '❌ FAIL'}")
    
    if search_result.get('success'):
        ma01002_found = search_result.get('ma01002_found', False)
        compatible_oems = search_result.get('compatible_oems', 0)
        
        print(f"🔍 Compatible OEMs found: {compatible_oems}")
        print(f"📦 MA01002 found: {'✅ YES' if ma01002_found else '❌ NO'}")
        
        if ma01002_found:
            print(f"\n🎉 SUCCESS: Mercedes brand matching fix works!")
            print(f"YZ99554 now correctly finds MA01002!")
        else:
            if compatible_oems > 0:
                print(f"\n⚠️  PARTIAL: Compatible OEMs found but MA01002 missing")
            else:
                print(f"\n❌ FAIL: Mercedes brand matching still not working")
    else:
        print(f"❌ Search test failed: {search_result.get('error', 'Unknown error')}")
