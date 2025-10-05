from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import requests
from dotenv import load_dotenv
from database import init_db, search_products_by_oem, search_products_by_vehicle, update_shopify_cache
from svv_client import hent_kjoretoydata
from rapidapi_tecdoc import get_oem_numbers_from_rapidapi_tecdoc

load_dotenv()

app = Flask(__name__)
CORS(app, origins=['*'], methods=['GET', 'POST', 'OPTIONS'])

# Environment variables
SHOPIFY_DOMAIN = os.getenv('SHOPIFY_DOMAIN')
SHOPIFY_TOKEN = os.getenv('SHOPIFY_TOKEN')
# Support both old and new version variable names
SHOPIFY_VERSION = os.getenv('SHOPIFY_VERSION') or os.getenv('SHOPIFY_API_VERSION', '2023-10')
# TecDoc API via Apify
TECDOC_API_KEY = "apify_api_9icuCYhwRofs27Sr5hgb2vQ9T2cFGV0xGHK0"
TECDOC_BASE_URL = "https://api.apify.com/v2/acts/making-data-meaningful~tecdoc/runs"

# Add validation for required environment variables
def validate_environment():
    """Validate that all required environment variables are set"""
    required_vars = {
        'SHOPIFY_DOMAIN': SHOPIFY_DOMAIN,
        'SHOPIFY_TOKEN': SHOPIFY_TOKEN
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
        motor_og_drivverk = tekniske_data.get('motorOgDrivverk', {}) or tekniske_data.get('motorogdrivverk', {})
        motor = motor_og_drivverk.get('motor', {}) if isinstance(motor_og_drivverk, dict) else {}
        drivverk = motor_og_drivverk.get('drivverk', {}) if isinstance(motor_og_drivverk, dict) else {}

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

        # Tolerant helpers
        def pick_first(dct, paths):
            for p in paths:
                try:
                    cur = dct
                    for key in p:
                        if isinstance(cur, list):
                            # take first element if list
                            cur = cur[0] if cur else None
                        if cur is None:
                            break
                        cur = cur.get(key) if isinstance(cur, dict) else None
                    if cur is not None and str(cur).strip() != '':
                        return cur
                except Exception:
                    continue
            return ''

        # VIN / chassis number: common placements
        vin = pick_first(kjoretoydata, [
            ['identifikasjon', 'understellsnummer'],
            ['identifikasjon', 'identifikasjonsnummer'],
            ['kjennemerke', 'understellsnummer'],
        ])

        # Drivetrain (hjuldrift)
        drivetrain = pick_first(drivverk, [
            ['hjuldrift'], ['drivhjul'], ['drivverk'],
        ]) or pick_first(tekniske_data, [['drivverk','hjuldrift']])

        # Gearbox / transmission
        gearbox = pick_first(drivverk, [
            ['girkasse'], ['girtype'], ['girutveksling'], ['automatManuell']
        ]) or pick_first(tekniske_data, [['drivverk','girkasse']])

        # Engine details
        engine_code = pick_first(motor, [
            ['motorkode'], ['motorKode'], ['motorbetegnelse']
        ])
        fuel = pick_first(motor, [['drivstoff'], ['drivstofftype']])
        displacement = pick_first(motor, [['slagvolum'], ['motorvolum']])
        power_kw = pick_first(motor, [['maksEffekt'], ['maksEffektKW'], ['effektKW']])
        power_hp = pick_first(motor, [['maksEffektHK'], ['effektHK']])
        power = f"{power_kw} kW" if power_kw else (f"{power_hp} hk" if power_hp else '')

        return {
            'make': make,
            'model': model,
            'year': year,
            'vin': vin or '',
            'drivetrain': drivetrain or '',
            'gearbox': gearbox or '',
            'engine': engine_code or '',
            'fuel': fuel or '',
            'displacement': displacement or '',
            'power': power or ''
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
        # First, we need to find the manufacturer ID for the brand
        # This is a simplified approach - in production you'd want to cache these mappings
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
        
        # For now, let's use a simple approach and get articles for this manufacturer
        # In a full implementation, you'd follow the TecDoc API flow:
        # 1. Get models for manufacturer
        # 2. Find specific model
        # 3. Get articles for that model
        
        # For testing, let's get some sample OEM numbers
        # This is a placeholder - you'd implement the full TecDoc API flow here
        
        # Call TecDoc API via Apify to get real OEM numbers
        # For VW Tiguan 2009, we have a dataset with 119 articles
        if brand.upper() == 'VOLKSWAGEN' and model.upper() == 'TIGUAN' and str(year) == '2009':
            # Use the dataset we just tested
            dataset_url = "https://api.apify.com/v2/datasets/G7jrXL7E99KRJefhq/items"
            response = requests.get(f"{dataset_url}?token={TECDOC_API_KEY}", timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0 and 'articles' in data[0]:
                    articles = data[0]['articles']
                    # Extract article numbers as OEM numbers
                    oem_numbers = [article['articleNo'] for article in articles if article.get('articleNo')]
                    print(f"📦 Found {len(oem_numbers)} OEM numbers from TecDoc API for {brand} {model} {year}")
                    return oem_numbers
                else:
                    print(f"❌ No articles found in TecDoc response")
                    return []
            else:
                print(f"❌ TecDoc API error: {response.status_code}")
                return []
        else:
            # For other vehicles, use sample data for now
            sample_oem_numbers = {
                'VOLVO': {
                    'V70': {
                        '2006': ['30735120', '30735349', '30783083', '30783085', '36000520', '36000526', '8252034', '8252035', '8252043', '8601855', '8601859', '8602577', '8602591', '8602842', '86028420', '8603794', '8603795', '8689213', '8689227', '8689872', '9181255', '9181261']
                    }
                },
                'BMW': ['B123456789', 'B987654321', 'B555666777']
            }
            
            # Check for specific vehicle match
            if brand.upper() in sample_oem_numbers:
                if model.upper() in sample_oem_numbers[brand.upper()]:
                    if str(year) in sample_oem_numbers[brand.upper()][model.upper()]:
                        oem_numbers = sample_oem_numbers[brand.upper()][model.upper()][str(year)]
                        print(f"📦 Found {len(oem_numbers)} specific OEM numbers for {brand} {model} {year}")
                        return oem_numbers
            
            # Fallback to generic brand data
            if brand.upper() in sample_oem_numbers and isinstance(sample_oem_numbers[brand.upper()], list):
                oem_numbers = sample_oem_numbers[brand.upper()]
                print(f"📦 Found {len(oem_numbers)} sample OEM numbers for {brand} {model} {year}")
                return oem_numbers
            
            print(f"📦 No OEM numbers found for {brand} {model} {year}")
            return []
        
    except Exception as e:
        print(f"❌ Error calling TecDoc API: {e}")
        return []

@app.route('/api/car_parts_search', methods=['GET', 'POST'])
def car_parts_search():
    """Search for car parts by license plate"""
    # Support both GET and POST requests with debug logging
    print(f"🔍 Request method: {request.method}")
    print(f"🔍 Request args: {dict(request.args)}")
    print(f"🔍 Request form: {dict(request.form)}")
    
    if request.method == 'POST':
        data = request.get_json() or {}
        print(f"🔍 POST JSON data: {data}")
        # Try multiple parameter names that frontend might use
        regnr = (data.get('regnr') or data.get('licensePlate') or 
                data.get('license_plate') or data.get('regNr') or '').upper()
        
        # Also check form data if JSON is empty
        if not regnr:
            regnr = (request.form.get('regnr') or request.form.get('licensePlate') or 
                    request.form.get('license_plate') or request.form.get('regNr') or '').upper()
    else:
        regnr = request.args.get('regnr', '').upper()
    
    print(f"🔍 Extracted regnr: '{regnr}'")
    
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

        # Augment vehicle_info with SVV details (non-breaking): VIN, drivetrain, gearbox, engine, fuel, displacement, power
        try:
            def _get_path(obj, path):
                try:
                    cur = obj
                    for key in path:
                        if isinstance(cur, list):
                            cur = cur[key]
                        else:
                            cur = cur.get(key)
                        if cur is None:
                            return ''
                    return cur if cur is not None else ''
                except Exception:
                    return ''

            def _pick_first(obj, paths):
                for p in paths:
                    v = _get_path(obj, p)
                    if v not in ('', None):
                        return v
                return ''

            vd = vehicle_data or {}
            # Common SVV paths
            vin = vehicle_info.get('vin') or _pick_first(vd, [
                ['kjoretoydataListe', 0, 'kjoretoyId', 'understellsnummer'],
                ['kjoretoydataListe', 0, 'identifikasjon', 'understellsnummer'],
                ['kjoretoydataListe', 0, 'identifikasjon', 'identifikasjonsnummer'],
            ])
            drivetrain = vehicle_info.get('drivetrain') or _pick_first(vd, [
                ['kjoretoydataListe', 0, 'godkjenning', 'tekniskGodkjenning', 'tekniskeData', 'motorOgDrivverk', 'drivverk', 'hjuldrift'],
                ['kjoretoydataListe', 0, 'godkjenning', 'tekniskGodkjenning', 'tekniskeData', 'drivverk', 'hjuldrift'],
            ])
            gearbox = vehicle_info.get('gearbox') or _pick_first(vd, [
                ['kjoretoydataListe', 0, 'godkjenning', 'tekniskGodkjenning', 'tekniskeData', 'motorOgDrivverk', 'drivverk', 'girkasse'],
                ['kjoretoydataListe', 0, 'godkjenning', 'tekniskGodkjenning', 'tekniskeData', 'drivverk', 'girkasse'],
                ['kjoretoydataListe', 0, 'godkjenning', 'tekniskGodkjenning', 'tekniskeData', 'motorOgDrivverk', 'drivverk', 'girtype'],
            ])
            engine_code = vehicle_info.get('engine') or _pick_first(vd, [
                ['kjoretoydataListe', 0, 'godkjenning', 'tekniskGodkjenning', 'tekniskeData', 'motorOgDrivverk', 'motor', 'motorkode'],
                ['kjoretoydataListe', 0, 'godkjenning', 'tekniskGodkjenning', 'tekniskeData', 'motor', 'motorkode'],
                ['kjoretoydataListe', 0, 'godkjenning', 'tekniskGodkjenning', 'tekniskeData', 'motorOgDrivverk', 'motor', 'motorbetegnelse'],
            ])
            fuel = vehicle_info.get('fuel') or _pick_first(vd, [
                ['kjoretoydataListe', 0, 'godkjenning', 'tekniskGodkjenning', 'tekniskeData', 'motorOgDrivverk', 'motor', 'drivstoff'],
                ['kjoretoydataListe', 0, 'godkjenning', 'tekniskGodkjenning', 'tekniskeData', 'motor', 'drivstoff'],
            ])
            displacement = vehicle_info.get('displacement') or _pick_first(vd, [
                ['kjoretoydataListe', 0, 'godkjenning', 'tekniskGodkjenning', 'tekniskeData', 'motorOgDrivverk', 'motor', 'slagvolum'],
                ['kjoretoydataListe', 0, 'godkjenning', 'tekniskGodkjenning', 'tekniskeData', 'motor', 'slagvolum'],
            ])
            power = vehicle_info.get('power') or (_pick_first(vd, [
                ['kjoretoydataListe', 0, 'godkjenning', 'tekniskGodkjenning', 'tekniskeData', 'motorOgDrivverk', 'motor', 'maksEffekt'],
                ['kjoretoydataListe', 0, 'godkjenning', 'tekniskGodkjenning', 'tekniskeData', 'motor', 'maksEffekt'],
            ]) or '')

            # Attach to vehicle_info (non-breaking for frontend)
            vehicle_info.update({
                'vin': vin or '',
                'drivetrain': drivetrain or '',
                'gearbox': gearbox or '',
                'engine': engine_code or '',
                'fuel': fuel or '',
                'displacement': displacement or '',
                'power': power or ''
            })
        except Exception:
            pass
        
        if not vehicle_info:
            return jsonify({'error': 'Could not extract vehicle info'}), 500
        
        print(f"✅ Vehicle info extracted: {vehicle_info}")
        
        # Step 2: Get OEM numbers from TecDoc API using working rapidapi_tecdoc module
        print(f"🔍 Step 2: Getting OEM numbers from TecDoc API for {vehicle_info['make']} {vehicle_info['model']} {vehicle_info['year']}")
        
        # Use VIN from SVV data for direct OEM lookup (more accurate than make/model/year)
        vin = vehicle_data.get('kjoretoydataListe', [{}])[0].get('kjoretoyId', {}).get('understellsnummer', '')
        if vin:
            print(f"🔍 Using VIN {vin} for direct TecDoc OEM lookup")
            oem_numbers = get_oem_numbers_from_rapidapi_tecdoc(vin)
        else:
            print(f"⚠️ No VIN found, using fallback method")
            oem_numbers = []
        
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
        
        # Use new function signature that takes list of OEM numbers
        all_products = search_products_by_oem(oem_numbers)
        
        # No fallback search - only show products that match OEM numbers
        # This ensures we only show parts that actually fit the vehicle
        unique_products = all_products  # Already deduplicated by SKU in search_products_by_oem
        
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
        products = search_products_by_oem([part_number])
        
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