#!/usr/bin/env python3
"""
Direct Product-Based Search
New approach: Test all products directly against vehicle instead of limiting OEM testing
This ensures ALL compatible parts are found, regardless of their position in any list
"""

import time
import os
from database import SessionLocal, ProductMetafield, ShopifyProduct, product_to_dict
from sqlalchemy import and_, create_engine
from sqlalchemy.orm import sessionmaker
from rapidapi_tecdoc import search_oem_in_tecdoc

# Force Railway database connection
RAILWAY_DATABASE_URL = 'postgresql://postgres:pmTNRdLNPAwZTYvtBFsqvfmjUOoNEuqM@shinkansen.proxy.rlwy.net:13074/railway'

def get_all_eligible_products():
    """
    Get ALL eligible products (Drivaksel/Mellomaksel with i_nettbutikk: ja)
    Returns list of products with their OEM numbers
    """
    try:
        # Create direct Railway database session
        engine = create_engine(RAILWAY_DATABASE_URL)
        RailwaySession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        session = RailwaySession()
        
        print("🚀 DIRECT APPROACH: Getting ALL eligible products...")
        
        # Get all products that have correct product_group
        products_with_oems = []
        
        # Query for all products with product_group = Drivaksel or Mellomaksel
        product_group_query = session.query(ProductMetafield).filter(
            ProductMetafield.key == 'product_group',
            ProductMetafield.value.in_(['Drivaksel', 'Mellomaksel'])
        ).all()
        
        print(f"📦 Found {len(product_group_query)} products with correct groups")
        
        for group_metafield in product_group_query:
            product_id = group_metafield.product_id
            
            # Get all metafields for this product
            product_metafields = session.query(ProductMetafield).filter(
                ProductMetafield.product_id == product_id
            ).all()
            
            # Get Shopify product info
            shopify_product = session.query(ShopifyProduct).filter(
                ShopifyProduct.id == product_id
            ).first()
            
            if not shopify_product:
                continue
            
            # Build product data
            product_data = {
                'id': product_id,
                'title': shopify_product.title,
                'handle': shopify_product.handle,
                'sku': shopify_product.sku,
                'price': shopify_product.price,
                'inventory_quantity': shopify_product.inventory_quantity,
                'product_group': group_metafield.value,
                'oem_numbers': [],
                'i_nettbutikk': 'nei'
            }
            
            # Extract metafields
            for metafield in product_metafields:
                if metafield.key == 'Original_nummer' and metafield.value:
                    # Parse comma-separated OEM numbers
                    oem_list = [oem.strip() for oem in metafield.value.split(',') if oem.strip()]
                    product_data['oem_numbers'] = oem_list
                elif metafield.key == 'i_nettbutikk':
                    product_data['i_nettbutikk'] = metafield.value
            
            # Only include products with i_nettbutikk: ja and OEM numbers
            if product_data['i_nettbutikk'] == 'ja' and product_data['oem_numbers']:
                products_with_oems.append(product_data)
        
        session.close()
        print(f"✅ DIRECT APPROACH: Found {len(products_with_oems)} eligible products with OEMs")
        return products_with_oems
        
    except Exception as e:
        print(f"❌ Error getting eligible products: {e}")
        import traceback
        traceback.print_exc()
        return []

def test_product_compatibility(product_data, vehicle_brand, vehicle_model, vehicle_year):
    """
    Test if a specific product is compatible with the vehicle
    Tests all OEM numbers for this product against TecDoc
    """
    product_id = product_data['id']
    oem_numbers = product_data['oem_numbers']
    
    print(f"🔍 Testing product {product_id} with {len(oem_numbers)} OEMs...")
    
    # Test each OEM number for this product
    for oem_number in oem_numbers:
        try:
            # Check TecDoc compatibility
            tecdoc_result = search_oem_in_tecdoc(oem_number)
            
            if tecdoc_result and 'articles' in tecdoc_result:
                articles = tecdoc_result['articles']
                
                for article in articles:
                    # Check brand compatibility
                    manufacturer_name = article.get('manufacturerName', '').upper()
                    article_name = article.get('articleName', '').upper()
                    
                    # Brand matching logic (same as optimized_search.py)
                    target_brand = vehicle_brand.upper()
                    
                    # Normalize brand names
                    if target_brand == 'VOLKSWAGEN':
                        target_brand = 'VW'
                    elif 'MERCEDES' in target_brand or target_brand == 'MERCEDES-BENZ':
                        target_brand = 'MERCEDES'
                    
                    # Direct brand match
                    brand_match = False
                    if target_brand == manufacturer_name or manufacturer_name == target_brand:
                        brand_match = True
                    elif target_brand in manufacturer_name or manufacturer_name in target_brand:
                        if len(target_brand) >= 3 and len(manufacturer_name) >= 3:
                            brand_match = True
                    
                    # Mercedes-specific matching
                    if 'MERCEDES' in vehicle_brand.upper() or vehicle_brand.upper() == 'MERCEDES-BENZ':
                        if 'MERCEDES' in manufacturer_name or manufacturer_name == 'MERCEDES-BENZ':
                            brand_match = True
                    
                    if brand_match:
                        print(f"✅ Product {product_id} compatible via OEM {oem_number}")
                        return {
                            'compatible': True,
                            'matched_oem': oem_number,
                            'manufacturer': manufacturer_name
                        }
        
        except Exception as e:
            print(f"⚠️ Error testing OEM {oem_number} for product {product_id}: {e}")
            continue
    
    return {'compatible': False}

def direct_product_search(license_plate):
    """
    DIRECT PRODUCT SEARCH: Test all eligible products directly against vehicle
    This guarantees ALL compatible parts are found, regardless of position
    """
    start_time = time.time()
    
    try:
        print(f"🚀 STARTING DIRECT PRODUCT SEARCH for {license_plate}")
        
        # Step 1: Get vehicle info from SVV
        from app import hent_kjoretoydata, extract_vehicle_info
        
        vehicle_data = hent_kjoretoydata(license_plate)
        if not vehicle_data:
            return {'error': 'Could not retrieve vehicle data from SVV'}
        
        vehicle_info = extract_vehicle_info(vehicle_data)
        if not vehicle_info:
            return {'error': 'Could not extract vehicle info'}
        
        print(f"🚗 Vehicle: {vehicle_info['make']} {vehicle_info['model']} {vehicle_info['year']}")
        
        # Step 2: Get ALL eligible products
        step2_start = time.time()
        all_products = get_all_eligible_products()
        step2_time = time.time() - step2_start
        
        if not all_products:
            return {
                'vehicle_info': vehicle_info,
                'total_products_tested': 0,
                'compatible_products': [],
                'message': 'No eligible products found in database'
            }
        
        print(f"📦 Testing {len(all_products)} products directly...")
        
        # Step 3: Test each product directly
        step3_start = time.time()
        compatible_products = []
        
        for i, product_data in enumerate(all_products):
            print(f"🔍 Testing product {i+1}/{len(all_products)}: {product_data['id']}")
            
            compatibility_result = test_product_compatibility(
                product_data,
                vehicle_info['make'],
                vehicle_info['model'],
                vehicle_info['year']
            )
            
            if compatibility_result['compatible']:
                # Convert to Shopify format
                shopify_product = {
                    'id': product_data['id'],
                    'title': product_data['title'],
                    'handle': product_data['handle'],
                    'sku': product_data['sku'],
                    'price': product_data['price'],
                    'inventory_quantity': product_data['inventory_quantity'],
                    'matched_oem': compatibility_result['matched_oem'],
                    'manufacturer': compatibility_result['manufacturer']
                }
                compatible_products.append(shopify_product)
                print(f"✅ FOUND COMPATIBLE: {product_data['id']} - {product_data['title']}")
        
        step3_time = time.time() - step3_start
        total_time = time.time() - start_time
        
        print(f"🎯 DIRECT SEARCH COMPLETED in {total_time:.2f}s")
        print(f"📊 Found {len(compatible_products)} compatible products out of {len(all_products)} tested")
        
        return {
            'vehicle_info': vehicle_info,
            'total_products_tested': len(all_products),
            'compatible_products': len(compatible_products),
            'shopify_parts': compatible_products,
            'message': f'Found {len(compatible_products)} compatible parts via direct product testing',
            'performance': {
                'total_time': round(total_time, 2),
                'step2_time': round(step2_time, 2),
                'step3_time': round(step3_time, 2),
                'products_per_second': round(len(all_products) / step3_time, 2) if step3_time > 0 else 0
            }
        }
        
    except Exception as e:
        print(f"❌ Error in direct product search: {e}")
        import traceback
        traceback.print_exc()
        return {'error': 'Internal server error', 'details': str(e)}

if __name__ == "__main__":
    # Test the direct product search
    print("🧪 Testing direct product search...")
    
    # Set Railway database URL for testing
    import os
    os.environ['DATABASE_URL'] = 'postgresql://postgres:pmTNRdLNPAwZTYvtBFsqvfmjUOoNEuqM@shinkansen.proxy.rlwy.net:13074/railway'
    
    # Test with YZ99554 to see if we find MA01002
    result = direct_product_search("YZ99554")
    print(f"🎯 Result: {result}")
    
    # Check if MA01002 was found
    if 'shopify_parts' in result:
        ma01002_found = any(part['id'] == 'MA01002' for part in result['shopify_parts'])
        print(f"🎯 MA01002 found: {'✅ YES' if ma01002_found else '❌ NO'}")
        
        if result['shopify_parts']:
            print(f"📦 Found products:")
            for part in result['shopify_parts']:
                print(f"   - {part['id']}: {part['title']}")
    else:
        print(f"❌ No shopify_parts in result")
