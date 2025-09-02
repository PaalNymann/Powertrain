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
    """Extract comprehensive vehicle info from SVV response"""
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
        
        # Basic vehicle info
        merke_liste = generelt.get('merke', [])
        make = merke_liste[0].get('merke', '').upper() if merke_liste else ''
        
        handelsbetegnelse_liste = generelt.get('handelsbetegnelse', [])
        model = handelsbetegnelse_liste[0].upper() if handelsbetegnelse_liste else ''
        
        forstegangsregistrering = kjoretoydata.get('forstegangsregistrering', {})
        registrert_dato = forstegangsregistrering.get('registrertForstegangNorgeDato', '')
        year = registrert_dato.split('-')[0] if registrert_dato else ''
        
        # Extended vehicle details
        # Chassis/VIN number - check multiple possible locations
        understellsnummer = generelt.get('understellsnummer', '')
        
        # If not found in generelt, check kjoretoyId (this is where it actually is!)
        if not understellsnummer:
            kjoretoy_id = kjoretoydata.get('kjoretoyId', {})
            understellsnummer = kjoretoy_id.get('understellsnummer', '')
            if understellsnummer:
                print(f"✅ Found chassis number in kjoretoyId: {understellsnummer}")
        else:
            print(f"✅ Found chassis number in generelt: {understellsnummer}")
        
        # Engine details
        motor_data = tekniske_data.get('motor', {})
        if isinstance(motor_data, list) and motor_data:
            motor_data = motor_data[0]  # Take first engine if multiple
        
        motor_volum = motor_data.get('slagvolum', '') if motor_data else ''
        motor_effekt = motor_data.get('maksEffekt', '') if motor_data else ''
        drivstoff_liste = motor_data.get('drivstoff', []) if motor_data else []
        fuel_type = drivstoff_liste[0].get('drivstoffKode', {}).get('kodeBeskrivelse', '') if drivstoff_liste else ''
        
        # Vehicle dimensions and weight
        dimensjoner = tekniske_data.get('dimensjoner', {})
        lengde = dimensjoner.get('lengde', '') if dimensjoner else ''
        bredde = dimensjoner.get('bredde', '') if dimensjoner else ''
        hoyde = dimensjoner.get('hoyde', '') if dimensjoner else ''
        
        vekter = tekniske_data.get('vekter', {})
        egenvekt = vekter.get('egenvekt', '') if vekter else ''
        totalvekt = vekter.get('tekniskTillattTotalvekt', '') if vekter else ''
        
        # Transmission
        girkasse_liste = tekniske_data.get('girkasse', [])
        transmission = girkasse_liste[0].get('girkasseType', {}).get('kodeBeskrivelse', '') if girkasse_liste else ''
        
        # Registration details
        kjennemerke = kjoretoydata.get('kjennemerke', '')
        
        # EU approval/type approval
        eu_godkjenning = teknisk_godkjenning.get('euGodkjenning', {})
        variant = eu_godkjenning.get('variant', '') if eu_godkjenning else ''
        versjon = eu_godkjenning.get('versjon', '') if eu_godkjenning else ''
        
        return {
            # Basic info (existing)
            'make': make,
            'model': model,
            'year': year,
            
            # Extended vehicle details
            'license_plate': kjennemerke,
            'chassis_number': understellsnummer,
            'engine_volume': f"{motor_volum} cm³" if motor_volum else '',
            'engine_power': f"{motor_effekt} kW" if motor_effekt else '',
            'fuel_type': fuel_type,
            'transmission': transmission,
            'length': f"{lengde} mm" if lengde else '',
            'width': f"{bredde} mm" if bredde else '',
            'height': f"{hoyde} mm" if hoyde else '',
            'curb_weight': f"{egenvekt} kg" if egenvekt else '',
            'total_weight': f"{totalvekt} kg" if totalvekt else '',
            'variant': variant,
            'version': versjon,
            'registration_date': registrert_dato
        }
    except Exception as e:
        print(f"❌ Error extracting vehicle info: {e}")
        import traceback
        traceback.print_exc()
        return None



# Force Railway deployment - implement correct TecDoc API approach
# OLD APIFY FUNCTION REMOVED - REPLACED BY RAPIDAPI TECDOC INTEGRATION

def get_available_oems_from_database(limit=None):
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
        
        # Apply limit if specified
        oem_list = list(all_oems)
        if limit and len(oem_list) > limit:
            print(f"🔧 Limiting to first {limit} OEMs for performance")
            return oem_list[:limit]
        
        return oem_list
        
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
                    elif 'MERCEDES' in target_brand or target_brand == 'MERCEDES-BENZ':
                        target_brand = 'MERCEDES'
                    
                    # Direct brand match (exact or contains)
                    brand_match = False
                    if target_brand == manufacturer_name or manufacturer_name == target_brand:
                        brand_match = True
                    elif target_brand in manufacturer_name or manufacturer_name in target_brand:
                        # Only allow partial matches for reasonable cases
                        if len(target_brand) >= 3 and len(manufacturer_name) >= 3:
                            brand_match = True
                    
                    # Mercedes-specific matching
                    if 'MERCEDES' in brand.upper() or brand.upper() == 'MERCEDES-BENZ':
                        if 'MERCEDES' in manufacturer_name or manufacturer_name == 'MERCEDES-BENZ':
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
                    
                    # Skip explicit rejection - let brand matching logic handle compatibility
                    # (Removed incompatible_brands logic that was incorrectly rejecting valid matches)
                
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
    """Search for car parts by license plate - OPTIMIZED VERSION"""
    if request.method == 'POST':
        data = request.get_json() or {}
        regnr = data.get('license_plate', '').upper()
    else:
        regnr = request.args.get('regnr', '').upper()
    
    if not regnr:
        return jsonify({'error': 'Missing license plate'}), 400
    
    print(f"🚗 Starting OPTIMIZED car parts search for license plate: {regnr}")
    
    try:
        # Use the optimized search function with OEM matching
        from optimized_search import optimized_car_parts_search
        result = optimized_car_parts_search(regnr)
        
        if 'error' in result:
            return jsonify(result), 500
        
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ Error in optimized car_parts_search: {e}")
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
        
        # Get ALL available OEMs from database and process in batches for complete coverage
        all_available_oems = get_available_oems_from_database()
        
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

@app.route('/api/cache/stats')
def cache_stats_endpoint():
    """Get TecDoc cache statistics"""
    try:
        from optimized_search import get_cache_stats
        stats = get_cache_stats()
        return jsonify({
            'message': 'Cache statistics retrieved',
            'cache_stats': stats
        })
    except Exception as e:
        return jsonify({'error': 'Failed to get cache stats', 'details': str(e)}), 500

@app.route('/api/cache/clear', methods=['POST'])
def clear_cache_endpoint():
    """Clear TecDoc cache"""
    try:
        from optimized_search import clear_tecdoc_cache
        clear_tecdoc_cache()
        return jsonify({'message': 'Cache cleared successfully'})
    except Exception as e:
        return jsonify({'error': 'Failed to clear cache', 'details': str(e)}), 500

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

@app.route('/api/debug/oem_matching/<license_plate>', methods=['GET'])
def debug_oem_matching(license_plate):
    """
    Debug endpoint to inspect OEM matching process step by step
    """
    from svv_client import hent_kjoretoydata
    from rapidapi_tecdoc import get_oem_numbers_from_rapidapi_tecdoc
    from optimized_search import search_products_by_oem_optimized
    from database import SessionLocal, ProductMetafield
    from sqlalchemy import text
    import traceback
    
    debug_info = {
        'license_plate': license_plate,
        'steps': {}
    }
    
    try:
        # Step 1: Get vehicle data
        debug_info['steps']['1_vehicle_data'] = {'status': 'starting'}
        vehicle_data = hent_kjoretoydata(license_plate)
        
        if not vehicle_data:
            debug_info['steps']['1_vehicle_data'] = {'status': 'failed', 'error': 'No vehicle data'}
            return jsonify(debug_info)
        
        vehicle_info = extract_vehicle_info(vehicle_data)
        debug_info['steps']['1_vehicle_data'] = {
            'status': 'success',
            'vehicle_info': {
                'make': vehicle_info.get('make'),
                'model': vehicle_info.get('model'),
                'year': vehicle_info.get('year'),
                'chassis_number': vehicle_info.get('chassis_number')
            }
        }
        
        # Step 2: Get TecDoc OEMs
        debug_info['steps']['2_tecdoc_oems'] = {'status': 'starting'}
        
        try:
            tecdoc_oems = get_oem_numbers_from_rapidapi_tecdoc(
                vehicle_info['make'], 
                vehicle_info['model'], 
                int(vehicle_info['year'])
            )
            
            debug_info['steps']['2_tecdoc_oems'] = {
                'status': 'success',
                'count': len(tecdoc_oems) if tecdoc_oems else 0,
                'oems': tecdoc_oems[:20] if tecdoc_oems else []  # First 20 for inspection
            }
            
        except Exception as e:
            debug_info['steps']['2_tecdoc_oems'] = {
                'status': 'failed',
                'error': str(e)
            }
            return jsonify(debug_info)
        
        # Step 3: Check database for these OEMs
        debug_info['steps']['3_database_check'] = {'status': 'starting'}
        
        session = SessionLocal()
        try:
            # Check total metafields
            count_query = text("SELECT COUNT(*) FROM product_metafields WHERE key = 'Original_nummer'")
            total_metafields = session.execute(count_query).scalar()
            
            # Test each TecDoc OEM against database
            oem_matches = []
            for oem in (tecdoc_oems[:10] if tecdoc_oems else []):  # Test first 10
                # Test exact match
                exact_query = text("""
                    SELECT COUNT(*) FROM product_metafields 
                    WHERE key = 'Original_nummer' AND value = :oem
                """)
                exact_count = session.execute(exact_query, {'oem': oem}).scalar()
                
                # Test LIKE patterns
                like_patterns = [f"{oem},%", f"%, {oem},%", f"%, {oem}"]
                like_count = 0
                for pattern in like_patterns:
                    like_query = text("""
                        SELECT COUNT(*) FROM product_metafields 
                        WHERE key = 'Original_nummer' AND value LIKE :pattern
                    """)
                    like_count += session.execute(like_query, {'pattern': pattern}).scalar()
                
                oem_matches.append({
                    'oem': oem,
                    'exact_matches': exact_count,
                    'like_matches': like_count,
                    'total_matches': exact_count + like_count
                })
            
            debug_info['steps']['3_database_check'] = {
                'status': 'success',
                'total_metafields': total_metafields,
                'oem_matches': oem_matches,
                'total_matching_oems': sum(1 for match in oem_matches if match['total_matches'] > 0)
            }
            
        except Exception as e:
            debug_info['steps']['3_database_check'] = {
                'status': 'failed',
                'error': str(e)
            }
        finally:
            session.close()
        
        # Step 4: Test search_products_by_oem_optimized for first few OEMs
        debug_info['steps']['4_search_function'] = {'status': 'starting'}
        
        search_results = []
        for oem in (tecdoc_oems[:3] if tecdoc_oems else []):  # Test first 3
            try:
                products = search_products_by_oem_optimized(oem)
                search_results.append({
                    'oem': oem,
                    'products_found': len(products) if products else 0,
                    'sample_products': [p.get('title', 'Unknown') for p in (products[:2] if products else [])]
                })
            except Exception as e:
                search_results.append({
                    'oem': oem,
                    'error': str(e)
                })
        
        debug_info['steps']['4_search_function'] = {
            'status': 'success',
            'search_results': search_results
        }
        
        # Summary
        debug_info['summary'] = {
            'tecdoc_oems_found': len(tecdoc_oems) if tecdoc_oems else 0,
            'database_matches': debug_info['steps']['3_database_check'].get('total_matching_oems', 0),
            'search_function_works': any(r.get('products_found', 0) > 0 for r in search_results),
            'diagnosis': 'Unknown'
        }
        
        # Diagnosis
        if debug_info['summary']['tecdoc_oems_found'] == 0:
            debug_info['summary']['diagnosis'] = 'TecDoc returns no OEMs'
        elif debug_info['summary']['database_matches'] == 0:
            debug_info['summary']['diagnosis'] = 'OEM format mismatch - TecDoc OEMs not found in database'
        elif not debug_info['summary']['search_function_works']:
            debug_info['summary']['diagnosis'] = 'search_products_by_oem_optimized() function issue'
        else:
            debug_info['summary']['diagnosis'] = 'Unknown issue - need deeper investigation'
        
        return jsonify(debug_info)
        
    except Exception as e:
        debug_info['error'] = str(e)
        debug_info['traceback'] = traceback.format_exc()
        return jsonify(debug_info), 500

@app.route('/api/debug/cache_oems/<license_plate>', methods=['GET'])
def debug_cache_oems(license_plate):
    """
    Debug endpoint to show what OEMs the cache system returns
    """
    from svv_client import hent_kjoretoydata
    from compatibility_matrix import get_oems_for_vehicle_from_cache
    from optimized_search import search_products_by_oem_optimized
    import traceback
    
    debug_info = {
        'license_plate': license_plate,
        'steps': {}
    }
    
    try:
        # Step 1: Get vehicle data
        vehicle_data = hent_kjoretoydata(license_plate)
        if not vehicle_data:
            return jsonify({'error': 'No vehicle data'})
        
        vehicle_info = extract_vehicle_info(vehicle_data)
        debug_info['vehicle_info'] = {
            'make': vehicle_info.get('make'),
            'model': vehicle_info.get('model'),
            'year': vehicle_info.get('year')
        }
        
        # Step 2: Get OEMs from cache
        try:
            cache_oems = get_oems_for_vehicle_from_cache(
                vehicle_info['make'], 
                vehicle_info['model'], 
                vehicle_info['year']
            )
            
            debug_info['cache_oems'] = {
                'count': len(cache_oems) if cache_oems else 0,
                'oems': cache_oems[:20] if cache_oems else []  # First 20 for inspection
            }
            
        except Exception as e:
            debug_info['cache_oems'] = {
                'error': str(e),
                'traceback': traceback.format_exc()
            }
            return jsonify(debug_info)
        
        # Step 3: Test each cache OEM against search function
        if cache_oems:
            search_results = []
            for i, oem in enumerate(cache_oems[:5]):  # Test first 5
                try:
                    products = search_products_by_oem_optimized(oem)
                    search_results.append({
                        'oem': oem,
                        'products_found': len(products) if products else 0,
                        'sample_products': [p.get('title', 'Unknown')[:50] for p in (products[:2] if products else [])]
                    })
                except Exception as e:
                    search_results.append({
                        'oem': oem,
                        'error': str(e)
                    })
            
            debug_info['search_results'] = search_results
        
        # Summary
        debug_info['summary'] = {
            'cache_oems_found': len(cache_oems) if cache_oems else 0,
            'search_matches': sum(1 for r in debug_info.get('search_results', []) if r.get('products_found', 0) > 0),
            'diagnosis': 'Unknown'
        }
        
        if debug_info['summary']['cache_oems_found'] == 0:
            debug_info['summary']['diagnosis'] = 'Cache returns no OEMs'
        elif debug_info['summary']['search_matches'] == 0:
            debug_info['summary']['diagnosis'] = 'Cache OEMs do not match database products'
        else:
            debug_info['summary']['diagnosis'] = 'Cache OEMs match some database products'
        
        return jsonify(debug_info)
        
    except Exception as e:
        debug_info['error'] = str(e)
        debug_info['traceback'] = traceback.format_exc()
        return jsonify(debug_info), 500

@app.route('/api/test/ma18002', methods=['GET'])
def test_ma18002():
    """
    Test if MA18002 exists in database and show its OEMs
    """
    from database import SessionLocal, ProductMetafield, ShopifyProduct
    from sqlalchemy import text
    import traceback
    
    result = {
        'ma18002_search': {},
        'nissan_oem_search': {},
        'summary': {}
    }
    
    session = SessionLocal()
    try:
        # Search for MA18002 by SKU/ID
        ma18002_query = text("""
            SELECT sp.id, sp.title, sp.sku, sp.price, sp.inventory_quantity
            FROM shopify_products sp
            WHERE sp.sku = 'MA18002' OR sp.id = 'MA18002'
            LIMIT 5
        """)
        ma18002_results = session.execute(ma18002_query).fetchall()
        
        result['ma18002_search'] = {
            'found': len(ma18002_results),
            'products': []
        }
        
        for row in ma18002_results:
            product_info = {
                'id': row[0],
                'title': row[1],
                'sku': row[2],
                'price': row[3],
                'inventory': row[4]
            }
            
            # Get metafields for this product
            metafields_query = text("""
                SELECT key, value
                FROM product_metafields
                WHERE product_id = :product_id
            """)
            metafields = session.execute(metafields_query, {'product_id': row[0]}).fetchall()
            product_info['metafields'] = {key: value for key, value in metafields}
            
            result['ma18002_search']['products'].append(product_info)
        
        # Search for known Nissan OEMs in database
        nissan_oems = ['37000-8H310', '37000-8H510', '37000-8H800', '370008H310', '370008H510', '370008H800']
        
        result['nissan_oem_search'] = {
            'tested_oems': nissan_oems,
            'matches': []
        }
        
        for oem in nissan_oems:
            # Test exact and LIKE patterns
            patterns = [
                ('exact', oem),
                ('start', f'{oem},%'),
                ('middle', f'%, {oem},%'),
                ('end', f'%, {oem}')
            ]
            
            for pattern_type, pattern in patterns:
                if pattern_type == 'exact':
                    oem_query = text("""
                        SELECT sp.id, sp.title, sp.sku, pm.value
                        FROM shopify_products sp
                        JOIN product_metafields pm ON sp.id = pm.product_id
                        WHERE pm.key = 'Original_nummer' AND pm.value = :pattern
                        LIMIT 3
                    """)
                else:
                    oem_query = text("""
                        SELECT sp.id, sp.title, sp.sku, pm.value
                        FROM shopify_products sp
                        JOIN product_metafields pm ON sp.id = pm.product_id
                        WHERE pm.key = 'Original_nummer' AND pm.value LIKE :pattern
                        LIMIT 3
                    """)
                
                oem_results = session.execute(oem_query, {'pattern': pattern}).fetchall()
                
                if oem_results:
                    result['nissan_oem_search']['matches'].append({
                        'oem': oem,
                        'pattern_type': pattern_type,
                        'pattern': pattern,
                        'matches': len(oem_results),
                        'products': [{'id': r[0], 'title': r[1], 'sku': r[2], 'oems': r[3]} for r in oem_results]
                    })
                    break  # Found match, no need to test other patterns
        
        # Summary
        result['summary'] = {
            'ma18002_exists': len(ma18002_results) > 0,
            'nissan_oems_found': len(result['nissan_oem_search']['matches']),
            'diagnosis': 'Unknown'
        }
        
        if not result['summary']['ma18002_exists']:
            result['summary']['diagnosis'] = 'MA18002 not synced to Shopify database'
        elif result['summary']['nissan_oems_found'] == 0:
            result['summary']['diagnosis'] = 'MA18002 exists but OEMs not found - sync issue'
        else:
            result['summary']['diagnosis'] = 'MA18002 and OEMs exist - matching logic issue'
        
        return jsonify(result)
        
    except Exception as e:
        result['error'] = str(e)
        result['traceback'] = traceback.format_exc()
        return jsonify(result), 500
    finally:
        session.close()

@app.route('/api/test/vin_extraction/<license_plate>', methods=['GET'])
def test_vin_extraction(license_plate):
    """Test VIN extraction from SVV data"""
    from svv_client import hent_kjoretoydata
    from rapidapi_tecdoc import extract_vin_from_svv, extract_engine_code_from_svv, extract_engine_size_from_svv
    import traceback
    
    result = {
        'license_plate': license_plate,
        'svv_data': {},
        'extracted_info': {},
        'diagnosis': ''
    }
    
    try:
        # Get SVV data
        svv_data = hent_kjoretoydata(license_plate)
        if not svv_data:
            result['diagnosis'] = 'No SVV data found'
            return jsonify(result)
        
        # Show relevant parts of SVV data structure
        if 'kjoretoydataListe' in svv_data and svv_data['kjoretoydataListe']:
            kjoretoydata = svv_data['kjoretoydataListe'][0]
            kjoretoy_id = kjoretoydata.get('kjoretoyId', {})
            
            result['svv_data'] = {
                'has_kjoretoydataListe': True,
                'kjoretoyId_keys': list(kjoretoy_id.keys()),
                'understellsnummer': kjoretoy_id.get('understellsnummer', 'NOT FOUND'),
                'kjennemerke': kjoretoy_id.get('kjennemerke', 'NOT FOUND')
            }
        
        # Extract VIN and other info
        vin = extract_vin_from_svv(svv_data)
        engine_code = extract_engine_code_from_svv(svv_data)
        engine_size = extract_engine_size_from_svv(svv_data)
        
        result['extracted_info'] = {
            'vin': vin,
            'engine_code': engine_code,
            'engine_size': engine_size
        }
        
        # Diagnosis
        if vin:
            result['diagnosis'] = f'VIN extracted successfully: {vin}'
        else:
            result['diagnosis'] = 'VIN extraction failed - check SVV data structure'
        
        return jsonify(result)
        
    except Exception as e:
        result['error'] = str(e)
        result['traceback'] = traceback.format_exc()
        return jsonify(result), 500

@app.route('/api/test/tecdoc_vin/<license_plate>', methods=['GET'])
def test_tecdoc_vin(license_plate):
    """Test TecDoc API directly with VIN from license plate"""
    from svv_client import hent_kjoretoydata
    from rapidapi_tecdoc import (
        extract_vin_from_svv, get_manufacturers, find_manufacturer_id,
        get_articles_by_vin, extract_oem_numbers_from_articles
    )
    import traceback
    
    result = {
        'license_plate': license_plate,
        'steps': {},
        'diagnosis': ''
    }
    
    try:
        # Step 1: Get VIN from SVV
        svv_data = hent_kjoretoydata(license_plate)
        if not svv_data:
            result['diagnosis'] = 'No SVV data'
            return jsonify(result)
        
        vin = extract_vin_from_svv(svv_data)
        if not vin:
            result['diagnosis'] = 'No VIN extracted'
            return jsonify(result)
        
        result['steps']['vin_extraction'] = {
            'success': True,
            'vin': vin
        }
        
        # Step 2: Get manufacturer ID for Nissan
        manufacturers_data = get_manufacturers()
        if not manufacturers_data:
            result['diagnosis'] = 'Failed to get manufacturers'
            return jsonify(result)
        
        manufacturers_list = manufacturers_data.get('manufacturers', [])
        manufacturer_id = find_manufacturer_id('NISSAN', manufacturers_list)
        if not manufacturer_id:
            result['diagnosis'] = 'Nissan manufacturer not found'
            return jsonify(result)
        
        result['steps']['manufacturer'] = {
            'success': True,
            'manufacturer_id': manufacturer_id
        }
        
        # Step 3: Test TecDoc VIN API for both product groups
        product_groups = [
            (100260, "Drivaksler"),
            (100270, "Mellomaksler")
        ]
        
        result['steps']['tecdoc_api_calls'] = []
        
        for product_group_id, group_name in product_groups:
            try:
                articles = get_articles_by_vin(vin, product_group_id, manufacturer_id)
                
                api_result = {
                    'product_group': group_name,
                    'product_group_id': product_group_id,
                    'success': articles is not None,
                    'articles_count': 0,
                    'oems_count': 0,
                    'sample_oems': []
                }
                
                if articles:
                    # Handle both dict and list formats
                    articles_list = articles.get('articles', []) if isinstance(articles, dict) else articles
                    api_result['articles_count'] = len(articles_list)
                    
                    if articles_list:
                        oems = extract_oem_numbers_from_articles({'articles': articles_list})
                        api_result['oems_count'] = len(oems)
                        api_result['sample_oems'] = oems[:10]  # First 10 OEMs
                
                result['steps']['tecdoc_api_calls'].append(api_result)
                
            except Exception as e:
                result['steps']['tecdoc_api_calls'].append({
                    'product_group': group_name,
                    'product_group_id': product_group_id,
                    'success': False,
                    'error': str(e)
                })
        
        # Summary and diagnosis
        total_oems = sum(call.get('oems_count', 0) for call in result['steps']['tecdoc_api_calls'])
        
        if total_oems > 0:
            result['diagnosis'] = f'SUCCESS: TecDoc API returned {total_oems} OEMs for VIN {vin}'
        else:
            successful_calls = [call for call in result['steps']['tecdoc_api_calls'] if call.get('success')]
            failed_calls = [call for call in result['steps']['tecdoc_api_calls'] if not call.get('success')]
            
            if failed_calls:
                result['diagnosis'] = f'TecDoc API calls failed for VIN {vin}'
            else:
                result['diagnosis'] = f'TecDoc API calls succeeded but returned 0 OEMs for VIN {vin}'
        
        return jsonify(result)
        
    except Exception as e:
        result['error'] = str(e)
        result['traceback'] = traceback.format_exc()
        return jsonify(result), 500

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