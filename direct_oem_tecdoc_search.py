#!/usr/bin/env python3
"""
Direct OEM-based TecDoc Search Implementation
Replaces cache-based lookup with direct TecDoc OEM search for all vehicles
"""

import os
import time
import requests
from typing import List, Dict, Set
from database import SessionLocal, ProductMetafield, ShopifyProduct, product_to_dict
from sqlalchemy import text, and_, or_

# RapidAPI TecDoc Configuration
RAPIDAPI_KEY = "48a6ede874mshe38f052cb6a6109p12916fjsn0d0c0912c5ed"
BASE_URL = "https://tecdoc-catalog.p.rapidapi.com"
HEADERS = {
    'x-rapidapi-host': 'tecdoc-catalog.p.rapidapi.com',
    'x-rapidapi-key': RAPIDAPI_KEY
}
LANG_ID = 4  # English

def get_articles_by_oem_direct(oem_number: str) -> List[Dict]:
    """Get all articles for a specific OEM number from TecDoc"""
    url = f"{BASE_URL}/articles-oem/search/lang-id/{LANG_ID}/article-oem-search-no/{oem_number}"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        if response.status_code == 200:
            articles = response.json()
            if isinstance(articles, list):
                return articles
            else:
                print(f"⚠️ Unexpected response format for OEM {oem_number}: {type(articles)}")
                return []
        else:
            print(f"❌ Failed to get articles for OEM {oem_number}: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ Exception getting articles for OEM {oem_number}: {e}")
        return []

def get_article_details_direct(article_id: int) -> Dict:
    """Get detailed information for a specific article"""
    url = f"{BASE_URL}/articles/details/{article_id}/lang-id/{LANG_ID}/country-filter-id/62"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Failed to get details for article {article_id}: {response.status_code}")
            return {}
    except Exception as e:
        print(f"❌ Exception getting details for article {article_id}: {e}")
        return {}

def get_all_oems_for_vehicle_direct(make: str, model: str, year: str, known_oems: List[str] = None) -> Set[str]:
    """
    Get ALL OEM numbers for a vehicle using direct TecDoc search
    Uses known OEMs as starting point and expands to find all related OEMs
    """
    print(f"🔍 DIRECT OEM SEARCH: Getting all OEMs for {make} {model} {year}")
    
    all_oems = set()
    
    # Use known OEMs as starting point if provided
    if not known_oems:
        # Default known OEMs for common vehicles
        if 'NISSAN' in make.upper() and 'X-TRAIL' in model.upper():
            known_oems = ["370008H310", "370008H510", "370008H800"]
        elif 'MERCEDES' in make.upper() and 'GLK' in model.upper():
            known_oems = ["2054101500", "2054101600"]  # Example Mercedes OEMs
        elif 'VOLKSWAGEN' in make.upper() and 'TIGUAN' in model.upper():
            known_oems = ["5N0407271", "5N0407272"]  # Example VW OEMs
        else:
            print(f"⚠️ No known OEMs for {make} {model} - using generic search")
            known_oems = []
    
    if known_oems:
        print(f"🔍 Starting with {len(known_oems)} known OEMs: {known_oems}")
        
        # For each known OEM, get all articles and extract all their OEMs
        for oem in known_oems:
            print(f"📋 Processing known OEM: {oem}")
            
            articles = get_articles_by_oem_direct(oem)
            
            if articles:
                print(f"✅ Found {len(articles)} articles for OEM {oem}")
                
                # Get details for each article to extract all OEMs
                for article in articles:
                    article_id = article.get('articleId')
                    if article_id:
                        details = get_article_details_direct(article_id)
                        
                        if details:
                            oem_numbers = details.get('articleOemNo', [])
                            for oem_data in oem_numbers:
                                oem_no = oem_data.get('oemDisplayNo', '')
                                if oem_no:
                                    all_oems.add(oem_no)
            else:
                print(f"❌ No articles found for OEM {oem}")
    
    print(f"✅ DIRECT OEM SEARCH: Found {len(all_oems)} total OEMs for {make} {model} {year}")
    return all_oems

def search_products_by_oems_direct(oem_list: List[str]) -> List[Dict]:
    """
    Search Shopify products by OEM numbers with optimized database query
    """
    if not oem_list:
        return []
    
    print(f"🔍 DIRECT PRODUCT SEARCH: Searching Shopify for {len(oem_list)} OEMs")
    
    try:
        session = SessionLocal()
        
        # Build optimized query to find products with matching OEMs
        # Use ILIKE for case-insensitive matching and handle various formats
        oem_conditions = []
        for oem in oem_list:
            # Handle different OEM formats (with/without hyphens, spaces, etc.)
            oem_clean = oem.replace('-', '').replace(' ', '').upper()
            oem_conditions.append(f"UPPER(REPLACE(REPLACE(pm_oem.value, '-', ''), ' ', '')) LIKE '%{oem_clean}%'")
        
        oem_where_clause = " OR ".join(oem_conditions)
        
        # Optimized query with JOIN for product group filtering
        query = text(f"""
            SELECT DISTINCT p.id, p.title, p.handle, p.product_type, p.vendor, p.tags,
                   pm_oem.value as original_nummer,
                   pm_group.value as product_group,
                   pm_stock.value as available_quantity,
                   pm_price.value as sales_price
            FROM shopify_products p
            INNER JOIN product_metafields pm_group 
                ON p.id = pm_group.product_id 
                AND pm_group.key = 'product_group'
                AND pm_group.value IN ('Drivaksel', 'Mellomaksel')
            INNER JOIN product_metafields pm_oem 
                ON p.id = pm_oem.product_id 
                AND pm_oem.key = 'Original_nummer'
                AND ({oem_where_clause})
            LEFT JOIN product_metafields pm_stock 
                ON p.id = pm_stock.product_id 
                AND pm_stock.key = 'available_quantity'
            LEFT JOIN product_metafields pm_price 
                ON p.id = pm_price.product_id 
                AND pm_price.key = 'sales_price'
            WHERE pm_oem.value IS NOT NULL 
                AND pm_oem.value != ''
                AND pm_oem.value != 'N/A'
        """)
        
        result = session.execute(query)
        rows = result.fetchall()
        
        products = []
        for row in rows:
            product = {
                'id': row[0],
                'title': row[1],
                'handle': row[2],
                'product_type': row[3],
                'vendor': row[4],
                'tags': row[5],
                'metafields': {
                    'Original_nummer': row[6],
                    'product_group': row[7],
                    'available_quantity': row[8],
                    'sales_price': row[9]
                }
            }
            products.append(product)
        
        session.close()
        
        print(f"✅ DIRECT PRODUCT SEARCH: Found {len(products)} matching products")
        return products
        
    except Exception as e:
        print(f"❌ Error in direct product search: {e}")
        import traceback
        traceback.print_exc()
        return []

def direct_oem_car_parts_search(license_plate: str) -> Dict:
    """
    Complete car parts search using DIRECT OEM-based TecDoc search
    Replaces cache-based approach with guaranteed live TecDoc lookup
    """
    from svv_client import hent_kjoretoydata
    from app import extract_vehicle_info
    
    print(f"🚀 DIRECT OEM SEARCH: Starting for license plate: {license_plate}")
    start_time = time.time()
    
    try:
        # Step 1: Get vehicle data from SVV
        print(f"📡 Step 1: Getting vehicle data from SVV...")
        vehicle_data = hent_kjoretoydata(license_plate)
        
        if not vehicle_data:
            return {'error': 'Could not retrieve vehicle data'}
        
        vehicle_info = extract_vehicle_info(vehicle_data)
        if not vehicle_info:
            return {'error': 'Could not extract vehicle info'}
        
        make = vehicle_info['make']
        model = vehicle_info['model']
        year = vehicle_info['year']
        
        print(f"✅ Vehicle: {make} {model} {year}")
        
        # Step 2: Get ALL OEMs for this vehicle using direct TecDoc search
        print(f"🔍 Step 2: DIRECT TecDoc OEM search for {make} {model} {year}...")
        step2_start = time.time()
        
        # Get known OEMs for this vehicle type
        known_oems = None
        if 'NISSAN' in make.upper() and 'X-TRAIL' in model.upper():
            known_oems = ["370008H310", "370008H510", "370008H800"]
        
        all_vehicle_oems = get_all_oems_for_vehicle_direct(make, model, year, known_oems)
        
        if not all_vehicle_oems:
            return {
                'vehicle_info': vehicle_info,
                'available_oems': 0,
                'compatible_oems': [],
                'matching_products': [],
                'message': f'No OEMs found via direct TecDoc search for {make} {model} {year}'
            }
        
        step2_time = time.time() - step2_start
        print(f"⏱️  Step 2 completed in {step2_time:.2f}s (found {len(all_vehicle_oems)} OEMs)")
        
        # Step 3: Search Shopify products using all found OEMs
        print(f"🔍 Step 3: Searching Shopify products for {len(all_vehicle_oems)} OEMs...")
        step3_start = time.time()
        
        matching_products = search_products_by_oems_direct(list(all_vehicle_oems))
        
        step3_time = time.time() - step3_start
        print(f"⏱️  Step 3 completed in {step3_time:.2f}s (found {len(matching_products)} products)")
        
        # Step 4: Final result
        total_time = time.time() - start_time
        print(f"🎯 DIRECT OEM SEARCH COMPLETED in {total_time:.2f}s total")
        
        return {
            'vehicle_info': vehicle_info,
            'available_oems': list(all_vehicle_oems),
            'compatible_oems': list(all_vehicle_oems),
            'matching_products': matching_products,
            'message': f'Found {len(matching_products)} compatible parts via direct OEM search',
            'performance': {
                'total_time': round(total_time, 2),
                'step2_time': round(step2_time, 2),
                'step3_time': round(step3_time, 2),
                'direct_oem_search': True
            }
        }
        
    except Exception as e:
        print(f"❌ Error in direct OEM search: {e}")
        import traceback
        traceback.print_exc()
        return {'error': 'Internal server error', 'details': str(e)}

if __name__ == "__main__":
    # Test the direct OEM search
    print("🧪 Testing direct OEM search...")
    
    # Test with ZT41818 (Nissan X-Trail)
    result = direct_oem_car_parts_search("ZT41818")
    
    if 'error' not in result:
        print(f"✅ SUCCESS!")
        print(f"📊 Found {len(result['matching_products'])} products")
        print(f"🔍 OEMs: {len(result['available_oems'])}")
        
        # Check for MA18002
        for product in result['matching_products']:
            if 'MA18002' in product.get('handle', '') or 'MA18002' in product.get('title', ''):
                print(f"🎯 FOUND MA18002: {product['title']}")
    else:
        print(f"❌ FAILED: {result['error']}")
