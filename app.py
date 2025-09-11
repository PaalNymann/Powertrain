from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import traceback
import time
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

# Simple in-memory cache for VIN -> OEM numbers to speed up repeated lookups
VIN_OEM_CACHE = {}

def _get_oems_cached(vin: str):
    try:
        ttl = int(os.getenv('OEM_CACHE_TTL_SECONDS', '600'))  # default 10 minutes
    except Exception:
        ttl = 600
    now = time.time()
    entry = VIN_OEM_CACHE.get(vin)
    if entry:
        expires_at, oems = entry
        if now < expires_at and oems:
            return oems
    oems = get_oem_numbers_from_rapidapi_tecdoc(vin)
    VIN_OEM_CACHE[vin] = (now + ttl, oems)
    return oems

# Simple in-memory cache for full search response per license plate (regnr)
RESPONSE_CACHE = {}

def _resp_cache_get(regnr: str):
    try:
        ttl = int(os.getenv('RESPONSE_CACHE_TTL_SECONDS', '60'))  # default 60 seconds
    except Exception:
        ttl = 60
    now = time.time()
    key = (regnr or '').strip().upper()
    entry = RESPONSE_CACHE.get(key)
    if entry:
        expires_at, data = entry
        if now < expires_at and isinstance(data, dict):
            return data
    return None

def _resp_cache_set(regnr: str, data: dict):
    try:
        ttl = int(os.getenv('RESPONSE_CACHE_TTL_SECONDS', '60'))
    except Exception:
        ttl = 60
    now = time.time()
    key = (regnr or '').strip().upper()
    RESPONSE_CACHE[key] = (now + ttl, data)

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

    # Fast path: serve cached response if recent
    cached_resp = _resp_cache_get(regnr)
    if cached_resp:
        return jsonify(cached_resp)

    try:
        # 1. Get vehicle info from SVV, including VIN
        vehicle_data = hent_kjoretoydata(regnr)
        if not vehicle_data or not vehicle_data.get('kjoretoydataListe'):
            return jsonify({'error': 'Could not retrieve vehicle data from SVV'}), 404
        
        vin = vehicle_data['kjoretoydataListe'][0].get('kjoretoyId', {}).get('understellsnummer')
        if not vin:
            return jsonify({'error': 'VIN not found in SVV data'}), 404

        # 2. Get OEM numbers from TecDoc using the VIN (cached for speed)
        oem_numbers = _get_oems_cached(vin)
        if not oem_numbers:
            return jsonify({'error': 'No compatible OEM numbers found from TecDoc for this vehicle'}), 404

        # 3. Search for products in our database using the OEM numbers from TecDoc (strict, no fallback)
        products = search_products_by_oems(oem_numbers)
        if not products:
            return jsonify({'error': 'No products found in the database for the retrieved OEM numbers'}), 404

        # Build a lightweight vehicle_info structure (best-effort; fields may be empty)
        vi_raw = vehicle_data['kjoretoydataListe'][0] if vehicle_data.get('kjoretoydataListe') else {}
        # Prefer nested tekniskGodkjenning.tekniskeData.generelt; fallback to tekniskeData.generelt
        tg = (vi_raw.get('tekniskGodkjenning') or {}).get('tekniskeData') or vi_raw.get('tekniskeData') or {}
        generelt = tg.get('generelt', {}) if isinstance(tg, dict) else {}

        # Make
        make = None
        merke_obj = generelt.get('merke') if isinstance(generelt, dict) else None
        if isinstance(merke_obj, dict):
            make = merke_obj.get('merkenavn') or merke_obj.get('navn')
        elif isinstance(merke_obj, str):
            make = merke_obj
        if not make and isinstance(vi_raw, dict):
            # last-resort fallbacks
            make = vi_raw.get('merke') or (vi_raw.get('kjoretoyId', {}) if isinstance(vi_raw.get('kjoretoyId'), dict) else {}).get('merke')
        if not make:
            # Deep fallback: search nested structures
            def _find_first_str(obj, keyset):
                if isinstance(obj, dict):
                    for k, v in obj.items():
                        if k in keyset:
                            if isinstance(v, str) and v.strip():
                                return v.strip()
                            if isinstance(v, dict):
                                for kk in ('merkenavn','navn','betegnelse','modellnavn','typebetegnelse','handelsbetegnelse'):
                                    vv = v.get(kk)
                                    if isinstance(vv, str) and vv.strip():
                                        return vv.strip()
                        res = _find_first_str(v, keyset)
                        if res:
                            return res
                elif isinstance(obj, list):
                    for it in obj:
                        res = _find_first_str(it, keyset)
                        if res:
                            return res
                return None
            make = _find_first_str(vi_raw, {'merkenavn','merke','navn','bilmerke'})

        # Model
        model = None
        hb = generelt.get('handelsbetegnelse') if isinstance(generelt, dict) else None
        if isinstance(hb, list):
            # Choose the first non-empty commercial designation (betegnelse or string)
            # Prefer values with length >= 2 to avoid single-letter series like "S"
            candidates = []
            for item in hb:
                if isinstance(item, dict):
                    v = item.get('betegnelse') or item.get('handelsbetegnelse') or item.get('modellnavn') or item.get('navn')
                    if isinstance(v, str) and v.strip():
                        candidates.append(v.strip())
                elif isinstance(item, str) and item.strip():
                    candidates.append(item.strip())
            # Prefer first with len >= 2
            for c in candidates:
                if len(c) >= 2:
                    model = c
                    break
            if not model and candidates:
                model = candidates[0]
        elif isinstance(hb, str):
            model = hb.strip() or None
        # If no model yet, search entire SVV payload specifically for 'handelsbetegnelse'
        if not model:
            def _first_handelsbetegnelse_value(val):
                if isinstance(val, list):
                    for it in val:
                        if isinstance(it, dict):
                            v = it.get('betegnelse') or it.get('handelsbetegnelse') or it.get('navn')
                            if isinstance(v, str) and len(v.strip()) >= 2:
                                return v.strip()
                        elif isinstance(it, str) and len(it.strip()) >= 2:
                            return it.strip()
                elif isinstance(val, dict):
                    v = val.get('betegnelse') or val.get('handelsbetegnelse') or val.get('navn')
                    if isinstance(v, str) and len(v.strip()) >= 2:
                        return v.strip()
                elif isinstance(val, str) and len(val.strip()) >= 2:
                    return val.strip()
                return None

            def _search_hb(obj):
                if isinstance(obj, dict):
                    if 'handelsbetegnelse' in obj:
                        got = _first_handelsbetegnelse_value(obj.get('handelsbetegnelse'))
                        if got:
                            return got
                    for vv in obj.values():
                        r = _search_hb(vv)
                        if r:
                            return r
                elif isinstance(obj, list):
                    for it in obj:
                        r = _search_hb(it)
                        if r:
                            return r
                return None
            model = _search_hb(vi_raw)

        if not model and isinstance(vi_raw, dict):
            # additional fallbacks
            model = vi_raw.get('handelsbetegnelse') or vi_raw.get('modell')
            if not model and isinstance(generelt, dict):
                model = generelt.get('betegnelse') or generelt.get('modell') or generelt.get('typebetegnelse')
        if not model:
            # Deep fallback
            def _find_first_str(obj, keyset):
                if isinstance(obj, dict):
                    for k, v in obj.items():
                        if k in keyset:
                            if isinstance(v, str) and v.strip():
                                return v.strip()
                            if isinstance(v, dict):
                                for kk in ('handelsbetegnelse','betegnelse','modellnavn','typebetegnelse','navn'):
                                    vv = v.get(kk)
                                    if isinstance(vv, str) and vv.strip():
                                        return vv.strip()
                        res = _find_first_str(v, keyset)
                        if res:
                            return res
                elif isinstance(obj, list):
                    for it in obj:
                        res = _find_first_str(it, keyset)
                        if res:
                            return res
                return None
            model = _find_first_str(vi_raw, {'handelsbetegnelse','betegnelse','modell','modellnavn','typebetegnelse'})

        # Year
        year = None
        fr = vi_raw.get('forstegangsregistrering') if isinstance(vi_raw, dict) else None
        if isinstance(fr, dict):
            ystr = fr.get('registrertForstegangNorgeDato') or fr.get('registrertForstegangDato')
            if isinstance(ystr, str) and len(ystr) >= 4:
                year = ystr[:4]
        if not year and isinstance(vi_raw, dict):
            ystr2 = vi_raw.get('forstegangsregistrertDato')
            if isinstance(ystr2, str) and len(ystr2) >= 4:
                year = ystr2[:4]

        vehicle_info = {
            'vin': vin,
            'make': make,
            'model': model,
            'year': year,
        }

        resp_obj = {
            'vehicle_info': vehicle_info,
            'shopify_parts': [product_to_dict(p) for p in products]
        }
        _resp_cache_set(regnr, resp_obj)
        return jsonify(resp_obj)

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
