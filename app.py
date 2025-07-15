from flask import Flask, request, jsonify
import requests
from flask_cors import CORS
import os
from dotenv import load_dotenv
from svv_client import hent_kjoretoydata

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app, origins="*")

# API Configuration
RACKBEAT_API_KEY = os.getenv('RACKBEAT_API_KEY')
SHOPIFY_DOMAIN = os.getenv('SHOPIFY_DOMAIN')
SHOPIFY_TOKEN = os.getenv('SHOPIFY_TOKEN')

def extract_vehicle_info(vehicle_data):
    """Extract only essential vehicle info: make, model, year"""
    try:
        vehicle_list = vehicle_data.get('kjoretoydataListe', [])
        if not vehicle_list:
            return None
            
        vehicle = vehicle_list[0]
        
        # Extract make
        make = "Unknown"
        generelt = vehicle.get('godkjenning', {}).get('tekniskGodkjenning', {}).get('tekniskeData', {}).get('generelt', {})
        merke_list = generelt.get('merke', [])
        if merke_list:
            make = merke_list[0].get('merke', 'Unknown')
        
        # Extract model
        model = "Unknown"
        handelsbetegnelse = generelt.get('handelsbetegnelse', [])
        if handelsbetegnelse:
            model = handelsbetegnelse[0]
        
        # Extract year
        year = "Unknown"
        reg_date = vehicle.get('forstegangsregistrering', {}).get('registrertForstegangNorgeDato', '')
        if reg_date:
            year = reg_date.split('-')[0]
        
        return {
            "make": make,
            "model": model,
            "year": year
        }
    except Exception as e:
        return None

@app.route('/api/statens_vegvesen')
def get_vehicle_info():
    kjennemerke = request.args.get('kjennemerke') or request.args.get('regnr')
    if not kjennemerke:
        return jsonify({"error": "Missing kjennemerke or regnr parameter"}), 400

    try:
        vehicle_data = hent_kjoretoydata(kjennemerke)
        return jsonify(vehicle_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/car_parts_search')
def car_parts_search():
    regnr = request.args.get('regnr')
    if not regnr:
        return jsonify({"error": "Missing regnr parameter"}), 400

    try:
        # Get vehicle data
        vehicle_data = hent_kjoretoydata(regnr)
        vehicle_info = extract_vehicle_info(vehicle_data)
        
        if not vehicle_info:
            return jsonify({"error": "Could not extract vehicle information"}), 400
        
        # Get Rackbeat data using the WORKING endpoint and method
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
                        if product.get('sales_price', 0) > 0 and product.get('available_quantity', 0) > 0:
                            rackbeat_parts.append({
                                "name": product.get('name', 'Unknown Part'),
                                "price": product.get('sales_price', 0),
                                "stock": product.get('available_quantity', 0),
                                "sku": product.get('number', ''),
                                "description": product.get('group', {}).get('name', '') if product.get('group') else '',
                                "cost_price": product.get('cost_price', 0)
                            })
                
            print(f"DEBUG: Rackbeat status {rackbeat_status}, processed {len(rackbeat_parts)} parts")
                
        except Exception as e:
            print(f"DEBUG: Rackbeat exception: {e}")
        
        return jsonify({
            "vehicle": vehicle_info,
            "available_parts": rackbeat_parts,
            "total_parts": len(rackbeat_parts),
            "rackbeat_status": rackbeat_status
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/rackbeat/parts')
def get_rackbeat_parts():
    try:
        url = "https://app.rackbeat.com/api/products"
        headers = {"Authorization": f"Bearer {RACKBEAT_API_KEY}"}
        
        response = requests.get(url, headers=headers)
        if response.status_code in [200, 206]:
            return jsonify(response.json())
        else:
            return jsonify({"error": f"Rackbeat API error: {response.status_code}"}), response.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/shopify/products', methods=['POST'])
def create_shopify_product():
    try:
        product_data = request.json
        
        url = f"https://{SHOPIFY_DOMAIN}/admin/api/2023-10/products.json"
        headers = {
            'X-Shopify-Access-Token': SHOPIFY_TOKEN,
            'Content-Type': 'application/json'
        }
        
        response = requests.post(url, json=product_data, headers=headers)
        
        if response.status_code == 201:
            return jsonify(response.json())
        else:
            return jsonify({"error": "Failed to create product"}), response.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8000)))

