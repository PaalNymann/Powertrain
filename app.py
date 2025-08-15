from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import requests
from dotenv import load_dotenv
from database import init_db, search_products_by_oem, update_shopify_cache, update_product_oem_metafields, ShopifyProduct
from svv_client import hent_kjoretoydata
import time

load_dotenv()

app = Flask(__name__)
CORS(app, origins=['*'], methods=['GET', 'POST', 'OPTIONS'])

# Environment variables
SHOPIFY_DOMAIN = os.getenv('SHOPIFY_DOMAIN')
SHOPIFY_TOKEN = os.getenv('SHOPIFY_TOKEN')
# Support both old and new version variable names
SHOPIFY_VERSION = os.getenv('SHOPIFY_VERSION') or os.getenv('SHOPIFY_API_VERSION', '2023-10')
# TecDoc API via Apify
TECDOC_API_KEY = os.getenv('TECDOC_API_KEY')
TECDOC_BASE_URL = 'https://api.apify.com/v2/acts/making-data-meaningful~tecdoc/run-sync-get-dataset-items'

# Add validation for required environment variables
def validate_environment():
    """Validate that all required environment variables are set"""
    required_vars = {
        'SHOPIFY_DOMAIN': SHOPIFY_DOMAIN,
        'SHOPIFY_TOKEN': SHOPIFY_TOKEN,
        'TECDOC_API_KEY': TECDOC_API_KEY
    }
    
    missing_vars = [var for var, value in required_vars.items() if not value]
    if missing_vars:
        print(f"❌ Missing required environment variables: {missing_vars}")
        return False
    
    print(f"✅ Environment validation passed")
    print(f"🔧 SHOPIFY_DOMAIN: {SHOPIFY_DOMAIN}")
    print(f"🔧 TECDOC_API_KEY: {TECDOC_API_KEY[:8]}...")
    return True

def extract_vehicle_info(vehicle_data):
    """Extract vehicle info from SVV response"""
    try:
        # SVV API returns kjoretoydataListe with kjoretoydata objects
        kjoretoydata_liste = vehicle_data.get('kjoretoydataListe', [])
        if not kjoretoydata_liste:
            print(f"❌ No kjoretoydataListe found in response")
            return None
        
        kjoretoydata = kjoretoydata_liste[0]  # Get first vehicle
        godkjenning = kjoretoydata.get('godkjenning', {})
        teknisk_godkjenning = godkjenning.get('tekniskGodkjenning', {})
        tekniske_data = teknisk_godkjenning.get('tekniskeData', {})
        generelt = tekniske_data.get('generelt', {})
        
        # Extract make from merke array
        merke_liste = generelt.get('merke', [])
        make = merke_liste[0].get('merke', '').upper() if merke_liste else ''
        
        # Extract model from handelsbetegnelse array
        handelsbetegnelse_liste = generelt.get('handelsbetegnelse', [])
        model = handelsbetegnelse_liste[0].upper() if handelsbetegnelse_liste else ''
        
        # Extract year from forstegangsregistrering
        forstegangsregistrering = kjoretoydata.get('forstegangsregistrering', {})
        registrert_dato = forstegangsregistrering.get('registrertForstegangNorgeDato', '')
        year = registrert_dato.split('-')[0] if registrert_dato else ''
        
        return {
            'make': make,
            'model': model,
            'year': year
        }
    except Exception as e:
        print(f"❌ Error extracting vehicle info: {e}")
        return None



# Force Railway deployment - implement correct TecDoc API approach
# OLD APIFY FUNCTION REMOVED - REPLACED BY RAPIDAPI TECDOC INTEGRATION

def get_available_oems_from_database():
    """Get all available OEM numbers from Rackbeat database for drivaksler/mellomaksler"""
    try:
        from database import SessionLocal, ProductMetafield
        session = SessionLocal()
        
        print("🔍 Querying database for available OEMs...")
        
        # Get product IDs that have product_group = 'Drivaksel' or 'Mellomaksel'
        product_group_metafields = session.query(ProductMetafield).filter(
            ProductMetafield.key == 'product_group',
            ProductMetafield.value.in_(['Drivaksel', 'Mellomaksel'])
        ).all()
        
        print(f"📦 Found {len(product_group_metafields)} products with correct product groups")
        
        if not product_group_metafields:
            session.close()
            return []
        
        # Get product IDs
        product_ids = [mf.product_id for mf in product_group_metafields]
        
        # Get OEM numbers for these products
        oem_metafields = session.query(ProductMetafield).filter(
            ProductMetafield.key == 'Original_nummer',
            ProductMetafield.product_id.in_(product_ids)
        ).all()
        
        print(f"🔧 Found {len(oem_metafields)} OEM metafields")
        
        all_oems = set()
        for metafield in oem_metafields:
            if metafield.value:
                # Split comma-separated OEM numbers
                oem_list = [oem.strip() for oem in metafield.value.split(',') if oem.strip()]
                all_oems.update(oem_list)
        
        session.close()
        print(f"✅ Total unique OEMs found: {len(all_oems)}")
        return list(all_oems)
        
    except Exception as e:
        print(f"❌ Error getting available OEMs: {e}")
        import traceback
        traceback.print_exc()
        return []

def check_oems_compatibility_with_vehicle(oem_list, brand, model, year):
    """Check which OEMs from the list are compatible with the vehicle using smart brand-based logic"""
    from rapidapi_tecdoc import search_oem_in_tecdoc
    
    compatible_oems = []
    
    print(f"🔍 Checking compatibility for {brand} {model} {year}")
    
    # Limit to first 50 OEMs to avoid timeout
    limited_oems = oem_list[:50]
    print(f"📋 Checking {len(limited_oems)} OEMs for compatibility...")
    
    for oem in limited_oems:
        try:
            # Search for this OEM in TecDoc
            result = search_oem_in_tecdoc(oem)
            
            if result.get('found') and result.get('articles'):
                articles = result.get('articles', [])
                
                # Check each article for brand compatibility
                is_compatible = False
                for article in articles:
                    manufacturer_name = article.get('manufacturerName', '').upper()
                    product_name = article.get('articleProductName', '').upper()
                    
                    # Brand matching logic
                    target_brand = brand.upper()
                    
                    # Normalize brand names for better matching
                    if target_brand == 'VOLKSWAGEN':
                        target_brand = 'VW'
                    
                    # Direct brand match (exact or contains)
                    brand_match = False
                    if target_brand == manufacturer_name or manufacturer_name == target_brand:
                        brand_match = True
                    elif target_brand in manufacturer_name or manufacturer_name in target_brand:
                        # Only allow partial matches for reasonable cases
                        if len(target_brand) >= 3 and len(manufacturer_name) >= 3:
                            brand_match = True
                    
                    if brand_match:
                        print(f"✅ OEM {oem} compatible: {manufacturer_name} part for {target_brand}")
                        is_compatible = True
                        break
                    
                    # Check if product name mentions the target brand or model
                    if target_brand in product_name or model.upper() in product_name:
                        print(f"✅ OEM {oem} compatible: Product '{product_name}' mentions {target_brand}/{model}")
                        is_compatible = True
                        break
                    
                    # Special case: VW/Volkswagen/Audi/Seat/Skoda group
                    vw_group = ['VW', 'VOLKSWAGEN', 'AUDI', 'SEAT', 'SKODA']
                    if target_brand in vw_group or brand.upper() in vw_group:
                        if any(vw_brand == manufacturer_name or manufacturer_name == vw_brand for vw_brand in vw_group):
                            print(f"✅ OEM {oem} compatible: VW Group part ({manufacturer_name}) for {target_brand}")
                            is_compatible = True
                            break
                    
                    # Explicitly reject incompatible brands
                    incompatible_brands = ['VOLVO', 'BMW', 'MERCEDES', 'FORD', 'TOYOTA', 'NISSAN']
                    if target_brand not in vw_group and manufacturer_name in incompatible_brands:
                        print(f"❌ OEM {oem} rejected: {manufacturer_name} part not compatible with {target_brand}")
                        break
                
                if is_compatible:
                    compatible_oems.append(oem)
                else:
                    print(f"❌ OEM {oem} not compatible: {manufacturer_name} part not suitable for {target_brand}")
            else:
                print(f"❌ OEM {oem} not found in TecDoc")
                
        except Exception as e:
            print(f"❌ Error checking OEM {oem}: {e}")
            continue
    
    print(f"🎯 Found {len(compatible_oems)} brand-compatible OEMs")
    return compatible_oems


@app.route('/api/car_parts_search', methods=['GET', 'POST'])
def car_parts_search():
    """Search for car parts by license plate"""
    if request.method == 'POST':
        data = request.get_json() or {}
        regnr = data.get('license_plate', '').upper()
    else:
        regnr = request.args.get('regnr', '').upper()
    
    if not regnr:
        return jsonify({'error': 'Missing license plate'}), 400
    
    print(f"🚗 Starting car parts search for license plate: {regnr}")
    
    try:
        # Step 1: Get vehicle data from SVV
        print(f"📡 Step 1: Getting vehicle data from SVV for {regnr}")
        vehicle_data = hent_kjoretoydata(regnr)
        
        print(f"📦 Raw vehicle data: {vehicle_data}")
        
        if not vehicle_data:
            return jsonify({'error': 'Could not retrieve vehicle data'}), 500
        
        # Extract vehicle info
        vehicle_info = extract_vehicle_info(vehicle_data)
        print(f"🔍 Extracted vehicle info: {vehicle_info}")
        
        if not vehicle_info:
            return jsonify({'error': 'Could not extract vehicle info'}), 500
        
        print(f"✅ Vehicle info extracted: {vehicle_info}")
        
        # Step 2: NEW STRATEGY - Get available OEMs from database and check TecDoc compatibility
        print(f"📋 Step 2: Getting available OEMs from Rackbeat database (limit to first 20 for performance)")
        available_oems = get_available_oems_from_database()[:20]  # Reduced limit for better performance
        print(f"🔍 Found {len(available_oems)} available OEMs in database (limited to 20 for performance)")
        
        if not available_oems:
            return jsonify({
                'vehicle_info': vehicle_info,
                'available_oems': 0,
                'compatible_oems': [],
                'matching_products': [],
                'message': 'No OEMs available in database'
            })
        
        # Step 3: Check which OEMs are compatible with this vehicle using RapidAPI TecDoc
        print(f"🔍 Step 3: Checking OEM compatibility with {vehicle_info['make']} {vehicle_info['model']} {vehicle_info['year']}")
        compatible_oems = check_oems_compatibility_with_vehicle(
            available_oems[:50],  # Test first 50 to avoid timeout
            vehicle_info['make'], 
            vehicle_info['model'], 
            vehicle_info['year']
        )
        
        print(f"✅ Found {len(compatible_oems)} compatible OEMs")
        
        if not compatible_oems:
            return jsonify({
                'vehicle_info': vehicle_info,
                'available_oems': len(available_oems),
                'compatible_oems': [],
                'matching_products': [],
                'message': f'No compatible OEMs found for this vehicle (tested {min(50, len(available_oems))} OEMs)'
            })
        
        # Step 4: Get products for compatible OEMs
        print(f"🛍️ Step 4: Getting products for compatible OEMs")
        
        all_matching_products = []
        
        for oem_number in compatible_oems:
            try:
                matching_products = search_products_by_oem(oem_number)
                
                if matching_products:
                    print(f"🔍 Found {len(matching_products)} products for OEM: {oem_number}")
                    
                    # Add OEM number to each product for reference
                    for product in matching_products:
                        product['matched_oem'] = oem_number
                    
                    all_matching_products.extend(matching_products)
                else:
                    print(f"🔍 No products found for OEM: {oem_number}")
                    
            except Exception as e:
                print(f"❌ Error searching for OEM {oem_number}: {e}")
                continue
        
        # Remove duplicates based on product ID
        unique_products = {}
        for product in all_matching_products:
            product_id = product.get('id')
            if product_id and product_id not in unique_products:
                unique_products[product_id] = product
        
        final_products = list(unique_products.values())
        
        print(f"✅ Found {len(final_products)} unique matching Shopify products")
        
        return jsonify({
            'vehicle_info': vehicle_info,
            'available_oems': len(available_oems),
            'compatible_oems': len(compatible_oems),
            'shopify_parts': final_products,  
            'message': f'Found {len(final_products)} compatible parts'
        })        
        
    except Exception as e:
        print(f"❌ Error in car_parts_search: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

@app.route('/api/part_number_search')
def part_number_search():
    """Search for parts by OEM number (free text search)"""
    part_number = request.args.get('part_number', '').strip()
    
    if not part_number:
        return jsonify({'error': 'Missing part number'}), 400
    
    print(f"🔍 Searching for part number: {part_number}")
    
    try:
        # Search in database with include_number=True for free text search
        products = search_products_by_oem(part_number, include_number=True)
        
        print(f"✅ Found {len(products)} matching products")
        
        return jsonify({
            'part_number': part_number,
            'count': len(products),
            'products': products
        })
        
    except Exception as e:
        print(f"❌ Error in part_number_search: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/')
def index():
    """Serve the main page"""
    return app.send_static_file('index.html') if os.path.exists('static/index.html') else '''
    <h1>🔧 Powertrain Parts API</h1>
    <p>API is running. Use the following endpoints:</p>
    <ul>
        <li><code>/api/car_parts_search?regnr=KH66644</code> - Search by license plate</li>
        <li><code>/api/part_number_search?part_number=8252034</code> - Search by part number</li>

        <li><code>/api/test_tecdoc</code> - Test TecDoc API</li>
        <li><code>/api/cache/update</code> - Update cache (POST)</li>
        <li><code>/health</code> - Health check</li>
    </ul>
    '''

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'message': 'API is running'})

@app.route('/api/test_svv')
def test_svv():
    """Test SVV API directly"""
    try:
        # Get license plate from query parameter
        test_regnr = request.args.get('regnr', '').upper()
        if not test_regnr:
            return jsonify({
                'success': False,
                'error': 'Missing regnr parameter'
            })
        
        vehicle_data = hent_kjoretoydata(test_regnr)
        vehicle_info = extract_vehicle_info(vehicle_data)
        return jsonify({
            'success': True,
            'svv_data': vehicle_data,
            'vehicle_info': vehicle_info
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })



@app.route('/api/test_tecdoc')
def test_tecdoc():
    """Test TecDoc API with vehicle data from license plate parameter"""
    try:
        # Get license plate from query parameter
        test_regnr = request.args.get('regnr', '').upper()
        
        if not test_regnr:
            return jsonify({
                'success': False,
                'error': 'License plate parameter (regnr) is required',
                'method': 'TecDoc API via Apify'
            })
        
        # Get vehicle data from SVV API first
        vehicle_data = hent_kjoretoydata(test_regnr)
        if not vehicle_data:
            return jsonify({
                'success': False,
                'error': 'Could not retrieve vehicle data from SVV',
                'method': 'TecDoc API via Apify'
            })
        
        vehicle_info = extract_vehicle_info(vehicle_data)
        if not vehicle_info:
            return jsonify({
                'success': False,
                'error': 'Could not extract vehicle info',
                'method': 'TecDoc API via Apify'
            })
        
        print(f"🧪 Testing RapidAPI TecDoc with: {vehicle_info['make']} {vehicle_info['model']} {vehicle_info['year']}")
        
        from rapidapi_tecdoc import get_oem_numbers_from_rapidapi_tecdoc
        
        oem_numbers = get_oem_numbers_from_rapidapi_tecdoc(
            vehicle_info['make'], 
            vehicle_info['model'], 
            vehicle_info['year'],
            svv_data=vehicle_data  # Pass full SVV data for VIN/engine code lookup
        )
        
        return jsonify({
            'success': True,
            'license_plate': test_regnr,
            'vehicle_info': vehicle_info,
            'oem_numbers': oem_numbers,
            'count': len(oem_numbers),
            'method': 'RapidAPI TecDoc'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'method': 'TecDoc API via Apify'
        })

@app.route('/api/cache/update', methods=['POST'])
def update_cache():
    """Update Shopify product cache"""
    try:
        print("🔄 Starting cache update...")
        
        all_products = []
        page = 1
        limit = 250  # Shopify's maximum per page
        
        while True:
            print(f"📡 Fetching page {page} from Shopify...")
            
            # Get products from Shopify with pagination
            url = f"https://{SHOPIFY_DOMAIN}/admin/api/{SHOPIFY_VERSION}/products.json?limit={limit}&page={page}"
            headers = {
                "X-Shopify-Access-Token": SHOPIFY_TOKEN,
                "Content-Type": "application/json"
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            products = data.get('products', [])
            
            if not products:
                print(f"📦 No more products found on page {page}")
                break
            
            print(f"📦 Retrieved {len(products)} products from page {page}")
            all_products.extend(products)
            
            # Check if we've reached the end
            if len(products) < limit:
                print(f"📦 Reached last page (page {page})")
                break
            
            page += 1
            
            # Safety check to prevent infinite loops
            if page > 100:
                print(f"⚠️ Safety limit reached at page {page}")
                break
        
        print(f"📦 Total products retrieved: {len(all_products)}")
        
        if all_products:
            # Update database cache
            update_shopify_cache(all_products)
            print(f"✅ Cache updated successfully with {len(all_products)} products")
        else:
            print(f"⚠️ No products found")
        
        return jsonify({
            'success': True,
            'message': f'Updated cache with {len(all_products)} products',
            'count': len(all_products),
            'pages_processed': page
        })
        
    except Exception as e:
        print(f"❌ Error updating cache: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/cache/stats')
def cache_stats():
    """Get cache statistics"""
    try:
        from database import SessionLocal
        from sqlalchemy import text
        session = SessionLocal()
        
        # Get actual table structure
        tables_result = session.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """))
        
        tables = [row[0] for row in tables_result]
        print(f"📋 Available tables: {tables}")
        
        # Get column info for shopify_products
        if 'shopify_products' in tables:
            columns_result = session.execute(text("""
                SELECT column_name, data_type
                FROM information_schema.columns 
                WHERE table_name = 'shopify_products'
                ORDER BY ordinal_position;
            """))
            
            columns = [(row[0], row[1]) for row in columns_result]
            print(f"🔍 shopify_products columns: {columns}")
            
            # Get row count
            count_result = session.execute(text("SELECT COUNT(*) FROM shopify_products;"))
            row_count = count_result.scalar()
            
            # Get sample data
            sample_result = session.execute(text("SELECT * FROM shopify_products LIMIT 3;"))
            sample_data = [dict(row._mapping) for row in sample_result]
            
            session.close()
            
            return jsonify({
                'cache_status': 'active',
                'tables': tables,
                'shopify_products_columns': columns,
                'total_products': row_count,
                'sample_data': sample_data
            })
        else:
            session.close()
            return jsonify({
                'cache_status': 'active',
                'tables': tables,
                'error': 'shopify_products table not found'
            })
            
    except Exception as e:
        print(f"❌ Error getting cache stats: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/metafields/update_oem', methods=['POST'])
def update_oem_metafields():
    """Update OEM metafields for products based on TecDoc search"""
    try:
        data = request.get_json()
        product_id = data.get('product_id')
        oem_numbers = data.get('oem_numbers', [])
        
        if not product_id:
            return jsonify({'error': 'Missing product_id'}), 400
        
        if not oem_numbers:
            return jsonify({'error': 'Missing oem_numbers'}), 400
        
        # Update the product's OEM metafield
        success = update_product_oem_metafields(product_id, oem_numbers)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Updated OEM metafield for product {product_id}',
                'oem_number': oem_numbers[0] if oem_numbers else None
            })
        else:
            return jsonify({'error': 'Failed to update OEM metafield'}), 500
            
    except Exception as e:
        print(f"❌ Error updating OEM metafields: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/metafields/stats')
def metafields_stats():
    """Get statistics on OEM metafield coverage in database"""
    try:
        from database import SessionLocal, ShopifyProduct
        session = SessionLocal()
        
        # Get total products count
        total_products = session.query(ShopifyProduct).count()
        
        # Get products with original_nummer metafield
        products_with_oem = session.query(ShopifyProduct).filter(
            ShopifyProduct.original_nummer_metafield.isnot(None),
            ShopifyProduct.original_nummer_metafield != ''
        ).count()
        
        # Calculate coverage percentage
        coverage_percentage = (products_with_oem / total_products * 100) if total_products > 0 else 0
        
        stats = {
            'total_products': total_products,
            'products_with_original_nummer': products_with_oem,
            'coverage_percentage': round(coverage_percentage, 2),
            'metafield_type': 'original_nummer',
            'status': 'active' if total_products > 0 else 'no_products'
        }
        
        session.close()
        return jsonify(stats)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/test_complete_workflow')
def test_complete_workflow():
    """Test the complete car parts search workflow"""
    try:
        # Get license plate from query parameter - no hardcoded fallback
        test_regnr = request.args.get('regnr', '').upper()
        
        if not test_regnr:
            return jsonify({
                'success': False,
                'error': 'License plate parameter (regnr) is required',
                'step': 'validation'
            })
        
        print(f"🧪 Testing complete workflow with license plate: {test_regnr}")
        
        # Step 1: Test SVV API
        print(f"📡 Step 1: Testing SVV API...")
        vehicle_data = hent_kjoretoydata(test_regnr)
        
        if not vehicle_data:
            return jsonify({
                'success': False,
                'error': 'SVV API failed',
                'step': 'svv_api'
            })
        
        vehicle_info = extract_vehicle_info(vehicle_data)
        if not vehicle_info:
            return jsonify({
                'success': False,
                'error': 'Vehicle info extraction failed',
                'step': 'vehicle_extraction',
                'raw_data': vehicle_data
            })
        
        print(f"✅ SVV API test passed: {vehicle_info}")
        
        # Step 2: Test RapidAPI TecDoc integration
        print(f"🔍 Step 2: Testing RapidAPI TecDoc integration...")
        from rapidapi_tecdoc import get_oem_numbers_from_rapidapi_tecdoc
        oem_numbers = get_oem_numbers_from_rapidapi_tecdoc(
            vehicle_info['make'],
            vehicle_info['model'],
            vehicle_info['year']
        )
        
        if not oem_numbers:
            print(f"❌ TecDoc API failed, trying local database for {vehicle_info['make']} {vehicle_info['model']} {vehicle_info['year']}")
            # The local_oem_database function is removed, so this block will now always return an empty list.
            # If a local database is needed, it must be re-implemented or removed.
            return jsonify({
                'success': False,
                'error': 'TecDoc API failed and local database is empty',
                'step': 'tecdoc_api',
                'vehicle_info': vehicle_info
            })
        
        print(f"✅ TecDoc API test passed: {len(oem_numbers)} OEM numbers found")
        
        # Step 3: Test database search
        print(f"🛍️ Step 3: Testing database search...")
        all_products = []
        for oem_number in oem_numbers[:5]:  # Test with first 5 OEM numbers
            products = search_products_by_oem(oem_number, include_number=False)
            if products:
                all_products.extend(products)
        
        print(f"✅ Database search test passed: {len(all_products)} products found")
        
        return jsonify({
            'success': True,
            'test_data': {
                'license_plate': test_regnr,
                'vehicle_info': vehicle_info,
                'oem_numbers_found': len(oem_numbers),
                'oem_numbers_sample': oem_numbers[:5],
                'products_found': len(all_products),
                'products_sample': all_products[:3] if all_products else []
            },
            'message': 'Complete workflow test passed successfully'
        })
        
    except Exception as e:
        print(f"❌ Complete workflow test failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Complete workflow test failed'
        })

@app.route('/api/database/raw_query')
def raw_database_query():
    """Direct database query to see actual structure"""
    try:
        import psycopg2
        import os
        
        # Connect directly to PostgreSQL
        DATABASE_URL = os.getenv('DATABASE_URL')
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        # Get table names
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        tables = [row[0] for row in cur.fetchall()]
        
        result = {'tables': tables}
        
        # Get shopify_products structure
        if 'shopify_products' in tables:
            cur.execute("""
                SELECT column_name, data_type
                FROM information_schema.columns 
                WHERE table_name = 'shopify_products'
                ORDER BY ordinal_position;
            """)
            columns = [(row[0], row[1]) for row in cur.fetchall()]
            result['shopify_products_columns'] = columns
            
            # Get row count
            cur.execute("SELECT COUNT(*) FROM shopify_products;")
            result['shopify_products_count'] = cur.fetchone()[0]
            
            # Get sample data
            cur.execute("SELECT * FROM shopify_products LIMIT 3;")
            sample_data = cur.fetchall()
            result['shopify_products_sample'] = sample_data
        
        # Get shopify_metafields structure if it exists
        if 'shopify_metafields' in tables:
            cur.execute("""
                SELECT column_name, data_type
                FROM information_schema.columns 
                WHERE table_name = 'shopify_metafields'
                ORDER BY ordinal_position;
            """)
            columns = [(row[0], row[1]) for row in cur.fetchall()]
            result['shopify_metafields_columns'] = columns
            
            # Get row count
            cur.execute("SELECT COUNT(*) FROM shopify_metafields;")
            result['shopify_metafields_count'] = cur.fetchone()[0]
        
        conn.close()
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ Error in raw database query: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/database/inspect')
def inspect_database():
    """Inspect the actual Railway database structure"""
    try:
        from database import SessionLocal
        from sqlalchemy import text
        session = SessionLocal()
        
        # Get all tables in the database
        tables_result = session.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """))
        
        tables = [row[0] for row in tables_result]
        print(f"📋 Available tables: {tables}")
        
        table_info = {}
        for table_name in tables:
            # Get column info for each table
            columns_result = session.execute(text(f"""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_name = '{table_name}'
                ORDER BY ordinal_position;
            """))
            
            columns = []
            for row in columns_result:
                columns.append({
                    'name': row[0],
                    'type': row[1],
                    'nullable': row[2]
                })
            
            # Get row count
            try:
                count_result = session.execute(text(f"SELECT COUNT(*) FROM {table_name};"))
                row_count = count_result.scalar()
            except:
                row_count = 'N/A'
            
            table_info[table_name] = {
                'columns': columns,
                'row_count': row_count
            }
        
        session.close()
        
        return jsonify({
            'message': 'Database structure inspection completed',
            'tables': table_info,
            'total_tables': len(tables)
        })
        
    except Exception as e:
        print(f"❌ Error inspecting database: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Failed to inspect database', 'details': str(e)}), 500

if __name__ == '__main__':
    # Validate environment variables first
    if not validate_environment():
        print("❌ Environment validation failed. Please check your environment variables.")
        exit(1)
    
    # Initialize database
    init_db()
    print("Database initialized successfully")
    
    # Start Flask app
    port = int(os.getenv('PORT', 8000))
    print(f"🚀 Starting Flask app on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False) 