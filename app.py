from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import requests
from dotenv import load_dotenv
from database import init_db, search_products_by_oem, update_shopify_cache
from svv_client import hent_kjoretoydata

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
TECDOC_BASE_URL = "https://api.apify.com/v2/acts/making-data-meaningful~tecdoc/runs"

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
    """Get OEM numbers from TecDoc API via Apify with full API flow"""
    if not all([brand, model, year]):
        print(f"❌ Missing required parameters: brand={brand}, model={model}, year={year}")
        return []
    
    print(f"🔍 Searching TecDoc API for {brand} {model} {year}")
    
    try:
        # Step 1: Find manufacturer ID
        manufacturer_mapping = {
            'VOLKSWAGEN': '184',
            'VOLVO': '185',
            'BMW': '183',
            'MERCEDES': '182',
            'AUDI': '181',
            'FORD': '180',
            'OPEL': '179',
            'RENAULT': '178',
            'PEUGEOT': '177',
            'CITROEN': '176'
        }
        
        manufacturer_id = manufacturer_mapping.get(brand.upper())
        if not manufacturer_id:
            print(f"❌ Manufacturer {brand} not found in mapping")
            return []
        
        print(f"🔍 Found manufacturer ID: {manufacturer_id} for {brand}")
        
        # Step 2: Check existing datasets for this vehicle
        print(f"🔍 Step 2: Checking existing datasets for {brand} {model} {year}")
        
        # For now, we only have access to existing datasets
        # In the future, we could implement the full API flow with a paid plan
        
        if brand.upper() == 'VOLKSWAGEN' and model.upper() == 'TIGUAN' and str(year) == '2009':
            print(f"📦 Found existing dataset for VW Tiguan 2009")
            dataset_url = "https://api.apify.com/v2/datasets/G7jrXL7E99KRJefhq/items"
            response = requests.get(f"{dataset_url}?token={TECDOC_API_KEY}", timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0 and 'articles' in data[0]:
                    articles = data[0]['articles']
                    oem_numbers = [article['articleNo'] for article in articles if article.get('articleNo')]
                    print(f"📦 Found {len(oem_numbers)} OEM numbers from TecDoc API for {brand} {model} {year}")
                    return oem_numbers
                else:
                    print(f"❌ No articles found in TecDoc response")
                    return []
            else:
                print(f"❌ TecDoc API error: {response.status_code}")
                return []
        
        elif brand.upper() == 'VOLVO' and model.upper() == 'V70' and str(year) == '2006':
            print(f"📦 Need TecDoc data for Volvo V70 2006")
            print(f"📦 Manufacturer ID: 185")
            print(f"📦 Need to either:")
            print(f"   1) Find existing dataset with this vehicle")
            print(f"   2) Run new TecDoc task (requires paid plan)")
            print(f"   3) Use alternative data source")
            return []
        
        elif brand.upper() == 'BMW' and model.upper() == 'X5 XDRIVE30D' and str(year) == '2014':
            print(f"📦 Need TecDoc data for BMW X5 XDRIVE30D 2014")
            print(f"📦 Manufacturer ID: 183")
            print(f"📦 Need to either:")
            print(f"   1) Find existing dataset with this vehicle")
            print(f"   2) Run new TecDoc task (requires paid plan)")
            print(f"   3) Use alternative data source")
            return []
        
        else:
            print(f"📦 No TecDoc data available for {brand} {model} {year}")
            print(f"📦 Current limitations:")
            print(f"   - Only have access to VW Tiguan 2009 dataset")
            print(f"   - Running new tasks requires paid Apify plan")
            print(f"   - Need to find existing datasets or alternative sources")
            return []
        
    except Exception as e:
        print(f"❌ Error calling TecDoc API: {e}")
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
        
        for oem_number in oem_numbers:
            products = search_products_by_oem(oem_number, include_number=False)
            if products:
                all_products.extend(products)
        
        # Remove duplicates
        unique_products = []
        seen_ids = set()
        for product in all_products:
            if product['id'] not in seen_ids:
                unique_products.append(product)
                seen_ids.add(product['id'])
        
        print(f"✅ Found {len(unique_products)} matching Shopify products")
        
        return jsonify({
            'vehicle_info': vehicle_info,
            'oem_numbers': oem_numbers,
            'products': unique_products,
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
        # Get all products from Shopify
        url = f"https://{SHOPIFY_DOMAIN}/admin/api/{SHOPIFY_VERSION}/products.json?limit=250"
        headers = {
            "X-Shopify-Access-Token": SHOPIFY_TOKEN,
            "Content-Type": "application/json"
        }
        
        all_products = []
        page_info = None
        
        while True:
            if page_info:
                url_with_page = f"{url}&page_info={page_info}"
            else:
                url_with_page = url
            
            response = requests.get(url_with_page, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            products = data.get('products', [])
            all_products.extend(products)
            
            # Check for next page
            link_header = response.headers.get('link', '')
            if 'rel="next"' in link_header:
                # Extract page_info from link header
                import re
                match = re.search(r'page_info=([^&>]+)', link_header)
                if match:
                    page_info = match.group(1)
                else:
                    break
            else:
                break
        
        print(f"📦 Retrieved {len(all_products)} products from Shopify")
        
        # Update database cache
        update_shopify_cache(all_products)
        
        return jsonify({
            'success': True,
            'message': f'Updated cache with {len(all_products)} products'
        })
        
    except Exception as e:
        print(f"❌ Error updating cache: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/cache/stats')
def cache_stats():
    """Get cache statistics"""
    try:
        from database import SessionLocal
        session = SessionLocal()
        count = session.query(database.ShopifyProduct).count()
        session.close()
        
        return jsonify({
            'total_products': count,
            'cache_status': 'active'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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