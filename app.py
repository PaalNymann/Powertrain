from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import requests
from dotenv import load_dotenv
from database import init_db, search_products_by_oem, update_shopify_cache, update_product_oem_metafields, ShopifyProduct
from svv_client import hent_kjoretoydata
import time
import traceback

load_dotenv()

app = Flask(__name__)
CORS(app, origins=['*'], methods=['GET', 'POST', 'OPTIONS'])

# Environment variables
SHOPIFY_DOMAIN = os.getenv('SHOPIFY_DOMAIN')
SHOPIFY_TOKEN = os.getenv('SHOPIFY_TOKEN')
SHOPIFY_VERSION = os.getenv('SHOPIFY_VERSION') or os.getenv('SHOPIFY_API_VERSION', '2023-10')
TECDOC_API_KEY = os.getenv('TECDOC_API_KEY')

# TecDoc API via RapidAPI - for Brand/Model/Year search
CATALOG_RAPIDAPI_KEY = os.getenv('TECDOC_API_KEY') # Re-using the same key
CATALOG_BASE_URL = "https://tecdoc-catalog.p.rapidapi.com"
CATALOG_HEADERS = {
    'x-rapidapi-host': 'tecdoc-catalog.p.rapidapi.com',
    'x-rapidapi-key': CATALOG_RAPIDAPI_KEY
}

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
        kjoretoydata_liste = vehicle_data.get('kjoretoydataListe', [])
        if not kjoretoydata_liste:
            return None
        
        kjoretoydata = kjoretoydata_liste[0]
        godkjenning = kjoretoydata.get('godkjenning', {})
        teknisk_godkjenning = godkjenning.get('tekniskGodkjenning', {})
        tekniske_data = teknisk_godkjenning.get('tekniskeData', {})
        generelt = tekniske_data.get('generelt', {})
        
        merke_liste = generelt.get('merke', [])
        make = merke_liste[0].get('merke', '').upper() if merke_liste else ''
        
        handelsbetegnelse_liste = generelt.get('handelsbetegnelse', [])
        model = handelsbetegnelse_liste[0].upper() if handelsbetegnelse_liste else ''
        
        forstegangsregistrering = kjoretoydata.get('forstegangsregistrering', {})
        registrert_dato = forstegangsregistrering.get('registrertForstegangNorgeDato', '')
        year = registrert_dato.split('-')[0] if registrert_dato else ''
        
        return {'make': make, 'model': model, 'year': year}
    except (IndexError, KeyError, TypeError):
        return None

def get_oems_by_vehicle_details(brand: str, model: str, year: str) -> list:
    """Gets OEM numbers from TecDoc using Brand, Model, and Year."""
    print(f"🚗 Getting OEM numbers for {brand} {model} ({year}) using Brand/Model/Year search.")

    # 1. Find Manufacturer ID
    try:
        man_url = f"{CATALOG_BASE_URL}/manufacturers/list"
        man_params = {'langId': 4, 'countryId': 62, 'typeId': 1}
        man_response = requests.get(man_url, headers=CATALOG_HEADERS, params=man_params, timeout=15)
        if man_response.status_code != 200:
            return []
        manufacturers = man_response.json()
        manufacturer_id = next((m['manufacturerId'] for m in manufacturers if m['manufacturerName'].upper() == brand.upper()), None)
        if not manufacturer_id:
            return []
    except requests.RequestException:
        return []

    # 2. Find Model ID (Vehicle ID)
    try:
        model_url = f"{CATALOG_BASE_URL}/models/list"
        model_params = {'langId': 4, 'countryId': 62, 'typeId': 1, 'manufacturerId': manufacturer_id}
        model_response = requests.get(model_url, headers=CATALOG_HEADERS, params=model_params, timeout=15)
        if model_response.status_code != 200:
            return []
        models = model_response.json()
        vehicle_id = next((m['vehicleId'] for m in models if model.upper() in m['vehicleName'].upper()), None)
        if not vehicle_id:
            return []
    except requests.RequestException:
        return []

    # 3. Get Articles and OEMs
    all_oems = set()
    product_groups = [(100260, "Drivaksler"), (100270, "Mellomaksler")]
    for group_id, group_name in product_groups:
        try:
            articles_url = f"{CATALOG_BASE_URL}/articles/list"
            articles_params = {'vehicleId': vehicle_id, 'productGroupId': group_id, 'langId': 4, 'countryId': 62, 'typeId': 1, 'page': 1, 'perPage': 100}
            articles_response = requests.get(articles_url, headers=CATALOG_HEADERS, params=articles_params, timeout=30)
            if articles_response.status_code == 200:
                articles = articles_response.json().get('articles', [])
                for article in articles:
                    article_id = article.get('articleId')
                    if article_id:
                        details_url = f"{CATALOG_BASE_URL}/articles/details"
                        details_payload = {'articleId': article_id, 'langId': 4, 'countryId': 62}
                        details_response = requests.post(details_url, headers=CATALOG_HEADERS, data=details_payload, timeout=30)
                        if details_response.status_code == 200:
                            oems = {oem['oemNumber'] for oem in details_response.json().get('oemNumbers', [])}
                            all_oems.update(oems)
        except requests.RequestException:
            continue

    return list(all_oems)

@app.route('/api/car_parts_search', methods=['GET'])
def car_parts_search():
    license_plate = request.args.get('regnr', '').upper()
    if not license_plate:
        return jsonify({'error': 'Missing regnr parameter'}), 400

    try:
        vehicle_data = hent_kjoretoydata(license_plate)
        if not vehicle_data or not vehicle_data.get('kjoretoydataListe'):
            return jsonify({'error': 'Vehicle not found'}), 404

        vehicle_info = extract_vehicle_info(vehicle_data)
        if not vehicle_info:
            return jsonify({'error': 'Could not extract vehicle info from SVV data'}), 500

        oem_numbers = get_oems_by_vehicle_details(
            brand=vehicle_info['make'],
            model=vehicle_info['model'],
            year=vehicle_info['year']
        )
        if not oem_numbers:
            return jsonify({'error': 'No compatible OEM numbers found from TecDoc for this vehicle'}), 404

        shopify_parts = search_products_by_oem(oem_numbers)

        return jsonify({
            'vehicle_info': vehicle_info,
            'oem_numbers_from_tecdoc': oem_numbers,
            'shopify_parts': shopify_parts
        })

    except Exception as e:
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()}), 500

# ... (all other functions from the original app.py should be here) ...

if __name__ == '__main__':
    if not validate_environment():
        exit(1)
    init_db()
    port = int(os.getenv('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=False)
