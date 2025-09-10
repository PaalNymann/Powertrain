from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import traceback
from dotenv import load_dotenv
from database import init_db, product_to_dict, search_products_by_oems, search_products_by_number
from rapidapi_tecdoc import get_oem_numbers_from_rapidapi_tecdoc
from svv_client import hent_kjoretoydata

# Load environment variables
load_dotenv()

app = Flask(__name__)
# Allow Shopify storefront to call our API (CORS)
allowed_origins = os.getenv("ALLOWED_ORIGINS", "https://bm0did-zc.myshopify.com")
CORS(app, resources={r"/api/*": {"origins": [o.strip() for o in allowed_origins.split(",") if o.strip()]}}, supports_credentials=False)

allowed_origin_list = [o.strip() for o in allowed_origins.split(",") if o.strip()]

@app.after_request
def add_cors_headers(resp):
    origin = request.headers.get('Origin')
    if origin and (origin in allowed_origin_list or "*" in allowed_origin_list):
        resp.headers['Access-Control-Allow-Origin'] = origin if origin in allowed_origin_list else "*"
        resp.headers['Vary'] = 'Origin'
        resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, X-Requested-With'
    return resp

@app.before_request
def before_request_func():
    init_db()

@app.route('/api/car_parts_search', methods=['GET', 'POST'])
def car_parts_search():
    # Support both GET ?regnr= and POST {"license_plate": "..."}
    regnr = None
    if request.method == 'GET':
        regnr = request.args.get('regnr')
    else:
        data = request.get_json(silent=True) or {}
        regnr = data.get('license_plate') or data.get('regnr')
    if not regnr:
        return jsonify({'error': 'Missing license plate (regnr)'}), 400

    try:
        # 1. Get vehicle info from SVV, including VIN
        vehicle_data = hent_kjoretoydata(regnr)
        if not vehicle_data or not vehicle_data.get('kjoretoydataListe'):
            return jsonify({'error': 'Could not retrieve vehicle data from SVV'}), 404
        
        vin = vehicle_data['kjoretoydataListe'][0].get('kjoretoyId', {}).get('understellsnummer')
        if not vin:
            return jsonify({'error': 'VIN not found in SVV data'}), 404

        # 2. Get OEM numbers from TecDoc using the VIN
        oem_numbers = get_oem_numbers_from_rapidapi_tecdoc(vin)
        if not oem_numbers:
            return jsonify({'error': 'No compatible OEM numbers found from TecDoc for this vehicle'}), 404

        # 3. Search for products in our database using the OEM numbers from TecDoc (strict, no fallback)
        products = search_products_by_oems(oem_numbers)
        if not products:
            return jsonify({'error': 'No products found in the database for the retrieved OEM numbers'}), 404

        # Build a lightweight vehicle_info structure (best-effort; fields may be empty)
        vi_raw = vehicle_data['kjoretoydataListe'][0]
        vehicle_info = {
            'vin': vin,
            'make': vi_raw.get('merke') if isinstance(vi_raw, dict) else None,
            'model': vi_raw.get('handelsbetegnelse') if isinstance(vi_raw, dict) else None,
            'year': vi_raw.get('forstegangsregistrertDato')[:4] if isinstance(vi_raw, dict) and vi_raw.get('forstegangsregistrertDato') else None,
        }

        return jsonify({
            'vehicle_info': vehicle_info,
            'shopify_parts': [product_to_dict(p) for p in products]
        })

    except Exception as e:
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()}), 500

@app.route('/api/search_by_number', methods=['GET'])
def search_by_number():
    number = request.args.get('number')
    if not number:
        return jsonify({'error': 'Missing number parameter'}), 400

    try:
        products = search_products_by_number(number)
        return jsonify([product_to_dict(p) for p in products])
    except Exception as e:
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8000))
    app.run(host='0.0.0.0', port=port)
