from flask import Flask, request, jsonify
import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# API Configuration
RACKBEAT_API_KEY = os.getenv('RACKBEAT_API_KEY')
SHOPIFY_DOMAIN = os.getenv('SHOPIFY_DOMAIN')
SHOPIFY_TOKEN = os.getenv('SHOPIFY_TOKEN')

@app.route('/api/statens_vegvesen')
def get_vehicle_info():
    regnr = request.args.get('regnr')
    if not regnr:
        return jsonify({"error": "Missing regnr parameter"}), 400
    
    if regnr == 'KB44781':
        return jsonify({
            "regnr": regnr,
            "merke": "Mercedes-Benz",
            "modell": "Sprinter",
            "arsmodell": 2019,
            "drivstoff": "Diesel",
            "motor": "2.1 CDI"
        })
    elif regnr == 'KH66644':
        return jsonify({
            "regnr": regnr,
            "merke": "Volkswagen", 
            "modell": "Tiguan",
            "registrert_i": "Kristiansand",
            "kjoretoygruppe": "M1 - Personbil",
            "status": "Registrert",
            "eu_kontroll": "Aktiv",
            "drivstoff": "Bensin",
            "motor": "TSI"
        })
    else:
        return jsonify({"error": "Vehicle not found"}), 404

@app.route('/api/mecaparts_parts')
def get_mecaparts_parts():
    regnr = request.args.get('regnr')
    if not regnr:
        return jsonify({"error": "Missing regnr parameter"}), 400
    
    try:
        url = f"https://{SHOPIFY_DOMAIN}/admin/api/2023-10/products.json"
        headers = {"X-Shopify-Access-Token": SHOPIFY_TOKEN}
        params = {"limit": 250}
        
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        
        data = response.json()
        products = data.get('products', [])
        
        all_parts = []
        for product in products:
            all_parts.append({
                "navn": product.get('title'),
                "pris": product.get('variants', [{}])[0].get('price', '0'),
                "tilgjengelighet": "På lager" if product.get('variants', [{}])[0].get('inventory_quantity', 0) > 0 else "Ikke på lager",
                "produkttype": product.get('product_type', 'Ukjent'),
                "leverandør": product.get('vendor', 'Ukjent'),
                "shopify_id": product.get('id')
            })
        
        return jsonify({
            "regnr": regnr,
            "deler": all_parts,
            "antall_deler": len(all_parts)
        })
        
    except Exception as e:
        return jsonify({"error": f"Shopify API error: {str(e)}"}), 500

@app.route('/api/rackbeat_parts')
def get_rackbeat_parts():
    try:
        url = "https://app.rackbeat.com/api/products"
        headers = {"Authorization": f"Bearer {RACKBEAT_API_KEY}"}
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        return jsonify(response.json())
        
    except Exception as e:
        return jsonify({"error": f"Rackbeat API error: {str(e)}"}), 500

@app.route('/api/car_parts_search')
def search_car_parts():
    regnr = request.args.get('regnr')
    if not regnr:
        return jsonify({"error": "Missing regnr parameter"}), 400
    
    # Get vehicle info
    with app.test_request_context(f'/api/statens_vegvesen?regnr={regnr}'):
        vehicle_response = get_vehicle_info()
        if isinstance(vehicle_response, tuple):
            vehicle_data, status_code = vehicle_response
            if status_code != 200:
                return vehicle_response
            vehicle_data = vehicle_data.get_json()
        else:
            vehicle_data = vehicle_response.get_json()
    
    # Get Mecaparts data
    with app.test_request_context(f'/api/mecaparts_parts?regnr={regnr}'):
        mecaparts_response = get_mecaparts_parts()
        if isinstance(mecaparts_response, tuple):
            mecaparts_data, _ = mecaparts_response
            mecaparts_data = mecaparts_data.get_json()
        else:
            mecaparts_data = mecaparts_response.get_json()
    
    # Get Rackbeat data - Accept both 200 and 206 status codes
    rackbeat_parts = []
    rackbeat_status = None
    
    try:
        url = "https://app.rackbeat.com/api/products"
        headers = {"Authorization": f"Bearer {RACKBEAT_API_KEY}"}
        params = {"limit": 50}
        
        response = requests.get(url, headers=headers, params=params)
        rackbeat_status = response.status_code
        
        # Accept both 200 (OK) and 206 (Partial Content) as success
        if response.status_code in [200, 206]:
            data = response.json()
            products = data.get('products', [])
            
            # Process products
            for product in products:
                if product and not product.get('is_barred', False):
                    rackbeat_parts.append({
                        "navn": product.get('name', 'Ukjent navn'),
                        "pris": product.get('sales_price', 0),
                        "tilgjengelighet": "På lager" if product.get('available_quantity', 0) > 0 else "Bestillingsvare",
                        "lager_antall": product.get('available_quantity', 0),
                        "produktgruppe": product.get('group', {}).get('name', 'Ukjent') if product.get('group') else 'Ukjent',
                        "produktnummer": product.get('number', ''),
                        "kostpris": product.get('cost_price', 0)
                    })
            
        print(f"DEBUG: Rackbeat status {rackbeat_status}, processed {len(rackbeat_parts)} parts")
            
    except Exception as e:
        print(f"DEBUG: Rackbeat exception: {e}")
    
    return jsonify({
        "kjøretøy": vehicle_data,
        "mecaparts_deler": mecaparts_data.get('deler', []),
        "antall_mecaparts": mecaparts_data.get('antall_deler', 0),
        "rackbeat_deler": rackbeat_parts,
        "antall_rackbeat_deler": len(rackbeat_parts),
        "totalt_antall_deler": mecaparts_data.get('antall_deler', 0) + len(rackbeat_parts),
        "rackbeat_status": rackbeat_status,
        "note": "Fixed to accept HTTP 206 (Partial Content) from Rackbeat API"
    })

@app.route('/')
def home():
    return jsonify({
        "message": "Norwegian Car Parts API - Status 206 Fix",
        "note": "Now accepts both HTTP 200 and 206 from Rackbeat API",
        "supported_plates": ["KB44781 (Mercedes Sprinter)", "KH66644 (Volkswagen Tiguan)"],
        "endpoints": [
            "/api/car_parts_search?regnr=KH66644"
        ]
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
