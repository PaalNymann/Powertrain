#!/usr/bin/env python3
"""
Debug Script for YZ99554 Search Failure
Comprehensive analysis of why license plate YZ99554 doesn't find MA01002
"""

import os
import requests
import json
import psycopg2
from dotenv import load_dotenv
from svv_client import hent_kjoretoydata
from app import extract_vehicle_info
from rapidapi_tecdoc import search_oem_in_tecdoc

load_dotenv()

DATABASE_URL = 'postgresql://postgres:pmTNRdLNPAwZTYvtBFsqvfmjUOoNEuqM@shinkansen.proxy.rlwy.net:13074/railway'

def debug_step1_vehicle_lookup():
    """Step 1: Debug vehicle lookup for YZ99554"""
    print("🚗 STEP 1: VEHICLE LOOKUP DEBUG")
    print("=" * 50)
    
    license_plate = "YZ99554"
    print(f"🔍 Looking up vehicle data for: {license_plate}")
    
    try:
        vehicle_data = hent_kjoretoydata(license_plate)
        print(f"📦 Raw SVV response: {json.dumps(vehicle_data, indent=2, ensure_ascii=False)}")
        
        if vehicle_data:
            vehicle_info = extract_vehicle_info(vehicle_data)
            print(f"✅ Extracted vehicle info: {vehicle_info}")
            return vehicle_info
        else:
            print(f"❌ No vehicle data returned from SVV")
            return None
            
    except Exception as e:
        print(f"❌ Error in vehicle lookup: {e}")
        import traceback
        traceback.print_exc()
        return None

def debug_step2_database_ma01002():
    """Step 2: Check if MA01002 exists in database with correct OEMs"""
    print(f"\n🗄️ STEP 2: DATABASE CHECK FOR MA01002")
    print("=" * 50)
    
    expected_oems = [
        "A2044102401", "A2044106901", "2044102401", "2044106901", 
        "A2044106701", "2044106701", "A2044101801", "2044101801", 
        "A2044102601", "2044102601", "A2044106701", "2044106701", 
        "A2214101701", "2214101701", "2044106901"
    ]
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # Check if MA01002 exists in shopify_products
        print(f"🔍 Checking if MA01002 exists in shopify_products...")
        cursor.execute("""
            SELECT id, title, handle, sku 
            FROM shopify_products 
            WHERE id = 'MA01002' OR handle = 'ma01002' OR sku = 'MA01002'
        """)
        
        product_results = cursor.fetchall()
        print(f"📦 Product search results: {product_results}")
        
        if not product_results:
            print(f"❌ MA01002 NOT FOUND in shopify_products table!")
            
            # Check if it exists with different ID format
            cursor.execute("""
                SELECT id, title, handle, sku 
                FROM shopify_products 
                WHERE title LIKE '%MA01002%' OR handle LIKE '%ma01002%' OR sku LIKE '%MA01002%'
            """)
            similar_results = cursor.fetchall()
            print(f"🔍 Similar products found: {similar_results}")
            
        else:
            product_id = product_results[0][0]
            print(f"✅ Found MA01002 with ID: {product_id}")
            
            # Check metafields for this product
            print(f"🔍 Checking metafields for product {product_id}...")
            cursor.execute("""
                SELECT key, value 
                FROM product_metafields 
                WHERE product_id = %s
                ORDER BY key
            """, (product_id,))
            
            metafields = cursor.fetchall()
            print(f"📋 All metafields for {product_id}:")
            for key, value in metafields:
                print(f"   {key}: {value}")
            
            # Check specifically for Original_nummer
            cursor.execute("""
                SELECT value 
                FROM product_metafields 
                WHERE product_id = %s AND key = 'Original_nummer'
            """, (product_id,))
            
            oem_result = cursor.fetchone()
            if oem_result:
                stored_oems = oem_result[0]
                print(f"✅ Original_nummer metafield: {stored_oems}")
                
                # Parse and compare OEMs
                if stored_oems:
                    stored_oem_list = [oem.strip() for oem in stored_oems.split(',')]
                    print(f"📋 Parsed OEMs from database: {stored_oem_list}")
                    
                    print(f"🔍 Checking which expected OEMs are present:")
                    for expected_oem in expected_oems:
                        if expected_oem in stored_oem_list:
                            print(f"   ✅ {expected_oem} - FOUND")
                        else:
                            print(f"   ❌ {expected_oem} - MISSING")
                            
                    # Check for extra OEMs
                    extra_oems = [oem for oem in stored_oem_list if oem not in expected_oems]
                    if extra_oems:
                        print(f"📋 Extra OEMs in database: {extra_oems}")
                        
                else:
                    print(f"❌ Original_nummer metafield is empty!")
            else:
                print(f"❌ No Original_nummer metafield found for {product_id}!")
        
        cursor.close()
        conn.close()
        
        return product_results[0] if product_results else None
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        import traceback
        traceback.print_exc()
        return None

def debug_step3_tecdoc_compatibility(vehicle_info):
    """Step 3: Test TecDoc compatibility for specific OEMs"""
    print(f"\n🔍 STEP 3: TECDOC COMPATIBILITY CHECK")
    print("=" * 50)
    
    if not vehicle_info:
        print(f"❌ No vehicle info available for TecDoc check")
        return []
    
    test_oems = ["A2044102401", "2044102401", "A2044106901", "2044106901", "A2214101701"]
    
    brand = vehicle_info['make']
    model = vehicle_info['model'] 
    year = vehicle_info['year']
    
    print(f"🚗 Testing compatibility for {brand} {model} {year}")
    print(f"🧪 Testing OEMs: {test_oems}")
    
    compatible_oems = []
    
    for oem in test_oems:
        print(f"\n🔍 Testing OEM: {oem}")
        try:
            result = search_oem_in_tecdoc(oem)
            print(f"📦 TecDoc result: {json.dumps(result, indent=2)}")
            
            if result.get('found') and result.get('articles'):
                articles = result.get('articles', [])
                print(f"📋 Found {len(articles)} articles")
                
                is_compatible = False
                for article in articles:
                    manufacturer_name = article.get('manufacturerName', '').upper()
                    product_name = article.get('articleProductName', '').upper()
                    
                    print(f"   🏭 Manufacturer: {manufacturer_name}")
                    print(f"   📦 Product: {product_name}")
                    
                    # Check brand compatibility
                    target_brand = brand.upper()
                    if 'MERCEDES' in target_brand or target_brand == 'MERCEDES-BENZ':
                        target_brand = 'MERCEDES'
                    
                    if (target_brand in manufacturer_name or 
                        manufacturer_name in target_brand or
                        target_brand in product_name or
                        'MERCEDES' in manufacturer_name):
                        print(f"   ✅ Compatible: {manufacturer_name} matches {target_brand}")
                        is_compatible = True
                        break
                    else:
                        print(f"   ❌ Not compatible: {manufacturer_name} doesn't match {target_brand}")
                
                if is_compatible:
                    compatible_oems.append(oem)
                    print(f"✅ OEM {oem} is COMPATIBLE")
                else:
                    print(f"❌ OEM {oem} is NOT COMPATIBLE")
            else:
                print(f"❌ OEM {oem} not found in TecDoc")
                
        except Exception as e:
            print(f"❌ Error testing OEM {oem}: {e}")
    
    print(f"\n🎯 Compatible OEMs found: {compatible_oems}")
    return compatible_oems

def debug_step4_product_search(compatible_oems):
    """Step 4: Test product search for compatible OEMs"""
    print(f"\n🛍️ STEP 4: PRODUCT SEARCH DEBUG")
    print("=" * 50)
    
    if not compatible_oems:
        print(f"❌ No compatible OEMs to search for")
        return []
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        all_found_products = []
        
        for oem in compatible_oems:
            print(f"\n🔍 Searching for products with OEM: {oem}")
            
            # Search in metafields
            cursor.execute("""
                SELECT DISTINCT sp.id, sp.title, sp.handle, sp.sku, pm.value as oem_value
                FROM shopify_products sp
                INNER JOIN product_metafields pm ON sp.id = pm.product_id
                WHERE (pm.key = 'Original_nummer' OR pm.key = 'number')
                AND pm.value LIKE %s
                AND pm.value IS NOT NULL
                AND pm.value != 'N/A'
            """, (f'%{oem}%',))
            
            products = cursor.fetchall()
            print(f"📦 Found {len(products)} products for OEM {oem}:")
            
            for product in products:
                print(f"   📦 {product[0]} - {product[1][:50]}... (OEM: {product[4]})")
                all_found_products.append(product)
        
        cursor.close()
        conn.close()
        
        return all_found_products
        
    except Exception as e:
        print(f"❌ Product search error: {e}")
        import traceback
        traceback.print_exc()
        return []

def debug_full_search_api():
    """Step 5: Test the full search API"""
    print(f"\n🌐 STEP 5: FULL API SEARCH TEST")
    print("=" * 50)
    
    backend_url = "https://web-production-0809b.up.railway.app"
    license_plate = "YZ99554"
    
    try:
        print(f"🚀 Testing full API search for {license_plate}...")
        response = requests.post(
            f"{backend_url}/api/car_parts_search",
            json={"license_plate": license_plate},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API Response:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            
            products = data.get('shopify_parts', [])
            print(f"\n📦 Found {len(products)} products via API")
            
            # Check if MA01002 is in results
            ma01002_found = False
            for product in products:
                if 'MA01002' in str(product.get('id', '')) or 'MA01002' in str(product.get('sku', '')):
                    ma01002_found = True
                    print(f"✅ MA01002 FOUND in API results: {product}")
                    break
            
            if not ma01002_found:
                print(f"❌ MA01002 NOT FOUND in API results")
                
        else:
            print(f"❌ API request failed: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ API test error: {e}")

def main():
    """Run complete debug analysis"""
    print("🔍 COMPREHENSIVE DEBUG ANALYSIS FOR YZ99554/MA01002")
    print("=" * 60)
    
    # Step 1: Vehicle lookup
    vehicle_info = debug_step1_vehicle_lookup()
    
    # Step 2: Database check
    product_info = debug_step2_database_ma01002()
    
    # Step 3: TecDoc compatibility
    compatible_oems = debug_step3_tecdoc_compatibility(vehicle_info)
    
    # Step 4: Product search
    found_products = debug_step4_product_search(compatible_oems)
    
    # Step 5: Full API test
    debug_full_search_api()
    
    # Summary
    print(f"\n📊 DEBUG SUMMARY")
    print("=" * 30)
    print(f"🚗 Vehicle found: {'✅' if vehicle_info else '❌'}")
    print(f"📦 MA01002 in database: {'✅' if product_info else '❌'}")
    print(f"🔍 Compatible OEMs: {len(compatible_oems)}")
    print(f"🛍️ Products found: {len(found_products)}")
    
    if vehicle_info and product_info and compatible_oems and found_products:
        print(f"\n🎯 ALL COMPONENTS WORKING - Search should succeed!")
    else:
        print(f"\n❌ ISSUE IDENTIFIED - One or more components failing")

if __name__ == "__main__":
    main()
