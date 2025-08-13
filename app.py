from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import requests
from dotenv import load_dotenv
from database import init_db, search_products_by_oem, update_shopify_cache, update_product_oem_metafields
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
TECDOC_BASE_URL = "https://api.apify.com/v2/acts/making-data-meaningful~tecdoc/run-sync"



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
def get_oem_numbers_from_tecdoc(brand, model, year):
    """Get OEM numbers from TecDoc API via Apify using correct endpoint format"""
    if not all([brand, model, year]):
        print(f"❌ Missing required parameters: brand={brand}, model={model}, year={year}")
        return []
    
    print(f"🔍 Searching TecDoc API for {brand} {model} {year}")
    
    try:
        # Use synchronous TecDoc API call via Apify
        url = f"{TECDOC_BASE_URL}?token={TECDOC_API_KEY}"
        
        print(f"🔍 Testing correct TecDoc API endpoints...")
        
        # Test 1: Search by OEM number directly (most reliable)
        print(f"📡 Test 1: Direct OEM search for {brand} {model} {year}")
        oem_search_params = {
            "selectPageType": "search-articles-by-article-oem-number",
            "langId": 4,
            "countryId": 1,
            "searchTerm": f"{brand} {model} {year}"
        }
        
        response = requests.post(url, json=oem_search_params, timeout=60)
        print(f"📦 Test 1 response: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"📦 Test 1 data: {data}")
            
            # Extract OEM numbers from response
            oem_numbers = extract_oem_numbers_from_response(data)
            if oem_numbers:
                print(f"✅ Success! Found {len(oem_numbers)} OEM numbers from direct search")
                return oem_numbers
        else:
            print(f"📦 Test 1 error: {response.text}")
        
        # Test 2: Get manufacturers first, then models, then articles
        print(f"📡 Test 2: 3-step approach with manufacturer/model lookup")
        
        # Step 2a: Get manufacturers for passenger cars
        print(f"📡 Step 2a: Getting manufacturers...")
        manufacturer_params = {
            "selectPageType": "get-manufacturers-by-type-id-lang-id-country-id",
            "langId": 4,
            "countryId": 1,
            "vehicleTypeId": 1
        }
        
        response = requests.post(url, json=manufacturer_params, timeout=60)
        print(f"📦 Manufacturers response: {response.status_code}")
        
        if response.status_code == 200:
            manufacturers_data = response.json()
            print(f"📦 Manufacturers data: {manufacturers_data}")
            
            # Find VOLVO manufacturer ID
            volvo_id = None
            if isinstance(manufacturers_data, list):
                for mfr in manufacturers_data:
                    if isinstance(mfr, dict) and mfr.get('name', '').upper() == brand.upper():
                        volvo_id = mfr.get('id')
                        break
            
            if volvo_id:
                print(f"✅ Found {brand} manufacturer ID: {volvo_id}")
                
                # Step 2b: Get models for VOLVO
                print(f"📡 Step 2b: Getting models for {brand}...")
                model_params = {
                    "selectPageType": "get-models",
                    "langId": 4,
                    "countryId": 1,
                    "vehicleTypeId": 1,
                    "manufacturerId": volvo_id
                }
                
                response = requests.post(url, json=model_params, timeout=60)
                print(f"📦 Models response: {response.status_code}")
                
                if response.status_code == 200:
                    models_data = response.json()
                    print(f"📦 Models data: {models_data}")
                    
                    # Find V70 model ID
                    v70_id = None
                    if isinstance(models_data, list):
                        for mdl in models_data:
                            if isinstance(mdl, dict) and mdl.get('name', '').upper() == model.upper():
                                v70_id = mdl.get('id')
                                break
                    
                    if v70_id:
                        print(f"✅ Found {model} model ID: {v70_id}")
                        
                        # Step 2c: Get articles for VOLVO V70 2006
                        print(f"📡 Step 2c: Getting articles for {brand} {model} {year}...")
                        article_params = {
                            "selectPageType": "get-article-list",
                            "langId": 4,
                            "countryId": 1,
                            "vehicleTypeId": 1,
                            "manufacturerId": volvo_id,
                            "modelId": v70_id,
                            "year": str(year)
                        }
                        
                        response = requests.post(url, json=article_params, timeout=60)
                        print(f"📦 Articles response: {response.status_code}")
                        
                        if response.status_code == 200:
                            articles_data = response.json()
                            print(f"📦 Articles data: {articles_data}")
                            
                            # Extract OEM numbers from response
                            oem_numbers = extract_oem_numbers_from_response(articles_data)
                            if oem_numbers:
                                print(f"✅ Success! Found {len(oem_numbers)} OEM numbers from 3-step approach")
                                return oem_numbers
                        else:
                            print(f"📦 Articles error: {response.text}")
                    else:
                        print(f"❌ Could not find {model} model ID")
                else:
                    print(f"📦 Models error: {response.text}")
            else:
                print(f"❌ Could not find {brand} manufacturer ID")
        else:
            print(f"📦 Manufacturers error: {response.text}")
        
        # Test 3: Try with vehicle type and year only
        print(f"📡 Test 3: Vehicle type and year search...")
        vehicle_params = {
            "selectPageType": "get-vehicle-types",
            "langId": 4,
            "countryId": 1
        }
        
        response = requests.post(url, json=vehicle_params, timeout=60)
        print(f"📦 Vehicle types response: {response.status_code}")
        
        if response.status_code == 200:
            vehicle_data = response.json()
            print(f"📦 Vehicle types data: {vehicle_data}")
        
        print(f"❌ All TecDoc API approaches failed")
        print(f"🔍 Recommendations:")
        print(f"   - Check Apify act configuration")
        print(f"   - Verify selectPageType values are correct")
        print(f"   - Try manual test in Apify dashboard")
        return []
        
    except Exception as e:
        print(f"❌ Error calling TecDoc API: {e}")
        return []

def extract_oem_numbers_from_response(data):
    """Extract OEM numbers from various TecDoc API response formats"""
    oem_numbers = []
    
    if not data:
        return oem_numbers
    
    # Handle different response formats
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                # Check for articles array
                if 'articles' in item:
                    for article in item['articles']:
                        if article.get('articleNo'):
                            oem_numbers.append(article['articleNo'])
                # Check for parts array
                elif 'parts' in item:
                    for part in item['parts']:
                        if part.get('oem_number'):
                            oem_numbers.append(part['oem_number'])
                # Check for items array
                elif 'items' in item:
                    for item_data in item['items']:
                        if item_data.get('oem') or item_data.get('partNumber'):
                            oem_numbers.append(item_data.get('oem') or item_data.get('partNumber'))
                # Check for direct OEM fields
                elif item.get('articleNo'):
                    oem_numbers.append(item['articleNo'])
                elif item.get('oem_number'):
                    oem_numbers.append(item['oem_number'])
    
    elif isinstance(data, dict):
        # Check for articles array
        if 'articles' in data:
            for article in data['articles']:
                if article.get('articleNo'):
                    oem_numbers.append(article['articleNo'])
        # Check for parts array
        elif 'parts' in data:
            for part in data['parts']:
                if part.get('oem_number'):
                    oem_numbers.append(part['oem_number'])
        # Check for items array
        elif 'items' in data:
            for item in data['items']:
                if item.get('oem') or item.get('partNumber'):
                    oem_numbers.append(item.get('oem') or item.get('partNumber'))
        # Check for direct OEM fields
        elif data.get('articleNo'):
            oem_numbers.append(data['articleNo'])
        elif data.get('oem_number'):
            oem_numbers.append(data['oem_number'])
    
    # Remove duplicates and return
    return list(set(oem_numbers))

@app.route('/api/car_parts_search')
def car_parts_search():
    """Search for car parts by license plate"""
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
        
        # Step 2: Get OEM numbers from TecDoc API
        print(f"🔍 Step 2: Getting OEM numbers from TecDoc API for {vehicle_info['make']} {vehicle_info['model']} {vehicle_info['year']}")
        
        oem_numbers = get_oem_numbers_from_tecdoc(
            vehicle_info['make'], 
            vehicle_info['model'], 
            vehicle_info['year']
        )
        
        if not oem_numbers:
            print(f"❌ No OEM numbers found for {vehicle_info['make']} {vehicle_info['model']} {vehicle_info['year']}")
            return jsonify({
                'vehicle_info': vehicle_info,
                'oem_numbers': [],
                'matching_products': [],
                'message': 'No OEM numbers found for this vehicle'
            })
        
        print(f"📦 Found {len(oem_numbers)} OEM numbers: {oem_numbers[:20]}")  # Show first 20
        
        # Step 3: Search Shopify products for OEM numbers
        print(f"🛍️ Step 3: Searching Shopify products for OEM numbers")
        
        all_matching_products = []
        updated_metafields = 0
        
        for oem_number in oem_numbers:
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
            'oem_numbers': oem_numbers,
            'matching_products': final_products,
            'total_matches': len(final_products),
            'metafields_updated': updated_metafields
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
        vehicle_data = hent_kjoretoydata('KH66644')
        vehicle_info = extract_vehicle_info(vehicle_data)
        return jsonify({
            'success': True,
            'vehicle_data': vehicle_data,
            'vehicle_info': vehicle_info
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })



@app.route('/api/test_tecdoc')
def test_tecdoc():
    """Test TecDoc API with sample vehicle data"""
    try:
        # Test with VW Tiguan 2009 (we have real data for this)
        test_brand = "VOLKSWAGEN"
        test_model = "TIGUAN"
        test_year = "2009"
        
        print(f"🧪 Testing TecDoc API with: {test_brand} {test_model} {test_year}")
        
        oem_numbers = get_oem_numbers_from_tecdoc(test_brand, test_model, test_year)
        
        return jsonify({
            'success': True,
            'test_data': {
                'brand': test_brand,
            'model': test_model,
                'year': test_year
            },
            'oem_numbers': oem_numbers,
            'count': len(oem_numbers),
            'method': 'TecDoc API via Apify'
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
        from database import SessionLocal, ShopifyProduct
        session = SessionLocal()
        count = session.query(ShopifyProduct).count()
        session.close()
        
        return jsonify({
            'total_products': count,
            'cache_status': 'active'
        })
        
    except Exception as e:
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
        # Test with a known working license plate
        test_regnr = "KH66644"  # VW Tiguan 2009
        
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
        
        # Step 2: Test TecDoc API
        print(f"🔍 Step 2: Testing TecDoc API...")
        oem_numbers = get_oem_numbers_from_tecdoc(
            vehicle_info['make'],
            vehicle_info['model'],
            vehicle_info['year']
        )
        
        if not oem_numbers:
            return jsonify({
                'success': False,
                'error': 'TecDoc API failed',
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

@app.route('/api/database/inspect')
def inspect_database():
    """Inspect the actual Railway database structure"""
    try:
        from database import inspect_database_structure
        columns = inspect_database_structure()
        
        return jsonify({
            'message': 'Database structure inspection completed',
            'columns': columns,
            'total_columns': len(columns)
        })
        
    except Exception as e:
        print(f"❌ Error inspecting database: {e}")
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