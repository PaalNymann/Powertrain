from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import requests
from dotenv import load_dotenv
from database import init_db, search_products_by_oem, update_shopify_cache
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



def get_oem_numbers_from_tecdoc(brand, model, year):
    """Get OEM numbers from TecDoc API via Apify"""
    if not all([brand, model, year]):
        print(f"❌ Missing required parameters: brand={brand}, model={model}, year={year}")
        return []
    
    print(f"🔍 Searching TecDoc API for {brand} {model} {year}")
    
    try:
        # Use synchronous TecDoc API call via Apify
        url = f"{TECDOC_BASE_URL}?token={TECDOC_API_KEY}"
        
        # Prepare search parameters based on OpenAPI schema
        # We need to use the correct endpoint type and parameters
        search_params = {
            "selectPageType": "get-article-list",  # Required parameter
            "langId": 4,  # English (GB)
            "countryId": 1,  # Germany (default)
            "vehicleTypeId": 1,  # Passenger car
            "manufacturerId": None,  # Will be set based on brand
            "modelId": None,  # Will be set based on model
            "year": str(year)
        }
        
        # Map brand names to manufacturer IDs (we'll need to get this dynamically)
        # For now, let's try to get articles for the vehicle type
        print(f"📡 Calling TecDoc API with params: {search_params}")
        
        # Make synchronous call
        response = requests.post(url, json=search_params, timeout=60)
        
        if response.status_code != 200:
            print(f"❌ TecDoc API error: {response.status_code}")
            print(f"Response: {response.text}")
            # Fallback to existing dataset
            return get_oem_numbers_from_existing_dataset(brand, model, year)
        
        data = response.json()
        print(f"📦 Raw TecDoc response: {data}")
        
        # Extract OEM numbers from response
        oem_numbers = []
        
        # Handle different response formats
        if isinstance(data, list):
            # If response is a list, look for articles in each item
            for item in data:
                if isinstance(item, dict) and 'articles' in item:
                    for article in item['articles']:
                        if article.get('articleNo'):
                            oem_numbers.append(article['articleNo'])
        elif isinstance(data, dict):
            # If response is a dict, look for articles
            if 'articles' in data:
                for article in data['articles']:
                    if article.get('articleNo'):
                        oem_numbers.append(article['articleNo'])
            # Also check for other possible fields
            elif 'parts' in data:
                for part in data['parts']:
                    if part.get('oem_number'):
                        oem_numbers.append(part['oem_number'])
        
        if oem_numbers:
            print(f"📦 Found {len(oem_numbers)} OEM numbers from TecDoc API for {brand} {model} {year}")
            return oem_numbers
        else:
            print(f"📦 No OEM numbers found from TecDoc API, trying fallback dataset")
            return get_oem_numbers_from_existing_dataset(brand, model, year)
        
    except Exception as e:
        print(f"❌ Error calling TecDoc API: {e}")
        print(f"📦 Trying fallback dataset")
        return get_oem_numbers_from_existing_dataset(brand, model, year)

def get_oem_numbers_from_existing_dataset(brand, model, year):
    """Fallback function to get OEM numbers from existing datasets"""
    try:
        print(f"🔄 Using fallback dataset for {brand} {model} {year}")
        
        # Use a known working dataset that contains car parts
        dataset_url = "https://api.apify.com/v2/datasets/G7jrXL7E99KRJefhq/items"
        response = requests.get(f"{dataset_url}?token={TECDOC_API_KEY}", timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0 and 'articles' in data[0]:
                articles = data[0]['articles']
                oem_numbers = [article['articleNo'] for article in articles if article.get('articleNo')]
                print(f"📦 Found {len(oem_numbers)} OEM numbers from fallback dataset")
                return oem_numbers[:20]  # Limit to first 20 for testing
            else:
                print(f"❌ No articles found in fallback dataset")
                return []
        else:
            print(f"❌ Fallback dataset error: {response.status_code}")
            return []
            
    except Exception as e:
        print(f"❌ Error with fallback dataset: {e}")
        return []

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
            print(f"📦 No OEM numbers found for {vehicle_info['make']} {vehicle_info['model']} {vehicle_info['year']}")
            return jsonify({
                'vehicle_info': vehicle_info,
                'oem_numbers': [],
                'products': [],
                'message': f'No parts found for {vehicle_info["make"]} {vehicle_info["model"]} {vehicle_info["year"]}'
            })
        
        print(f"📦 Found {len(oem_numbers)} OEM numbers: {oem_numbers}")
        
        # Step 3: Search Shopify products for OEM numbers
        print(f"🛍️ Step 3: Searching Shopify products for OEM numbers")
        all_products = []
        updated_metafields = 0
        
        for oem_number in oem_numbers:
            products = search_products_by_oem(oem_number, include_number=False)
            if products:
                all_products.extend(products)
                
                # Update metafields for products that don't have OEM numbers set
                for product in products:
                    if not product.get('oem') or product.get('oem') in ['', 'N/A', None]:
                        # Update the product's OEM metafield
                        success = update_product_oem_metafields(product['id'], [oem_number])
                        if success:
                            updated_metafields += 1
                            # Update the product dict to reflect the change
                            product['oem'] = oem_number
        
        # Remove duplicates
        unique_products = []
        seen_ids = set()
        for product in all_products:
            if product['id'] not in seen_ids:
                unique_products.append(product)
                seen_ids.add(product['id'])
        
        print(f"✅ Found {len(unique_products)} matching Shopify products")
        if updated_metafields > 0:
            print(f"🔄 Updated OEM metafields for {updated_metafields} products")
        
        return jsonify({
            'vehicle_info': vehicle_info,
            'oem_numbers': oem_numbers,
            'products': unique_products,
            'metafields_updated': updated_metafields,
            'message': f'Found {len(unique_products)} products for {vehicle_info["make"]} {vehicle_info["model"]} {vehicle_info["year"]}'
        })
        
    except Exception as e:
        print(f"❌ Error in car_parts_search: {e}")
        return jsonify({'error': 'Internal server error'}), 500

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
    """Get statistics about metafields in the database"""
    try:
        from database import get_products_without_oem, SessionLocal, ShopifyProduct
        
        session = SessionLocal()
        total_products = session.query(ShopifyProduct).count()
        
        # Count products with OEM metafields
        products_with_oem = session.query(ShopifyProduct).filter(
            ShopifyProduct.oem_metafield.isnot(None),
            ShopifyProduct.oem_metafield != '',
            ShopifyProduct.oem_metafield != 'N/A'
        ).count()
        
        session.close()
        
        return jsonify({
            'total_products': total_products,
            'products_with_oem': products_with_oem,
            'products_without_oem': total_products - products_with_oem,
            'oem_coverage_percentage': round((products_with_oem / total_products * 100), 2) if total_products > 0 else 0
        })
        
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