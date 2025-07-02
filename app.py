from flask import Flask, request, jsonify
import requests
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

app = Flask(__name__)

@app.route("/api/vehicle_lookup", methods=["GET"])
def vehicle_lookup():
    regnr = request.args.get("regnr", "").upper()
    if regnr == "KB44781":
        return jsonify({
            "regnr": "KB44781",
            "merke": "Nissan",
            "modell": "Qashqai",
            "år": 2018,
            "typegodkjenning": "EF123456",
            "drivverk": "4x4",
            "har_mellomaksel": True
        })
    else:
        return jsonify({"error": "Kjøretøy ikke funnet"}), 404

@app.route("/api/mecaparts_parts", methods=["GET"])
def mecaparts_parts():
    regnr = request.args.get("regnr", "").upper()
    if regnr == "KB44781":
        return jsonify({
            "parts": [
                {"delnr": "MEC-12345", "navn": "Bremseklosser sett", "pris": 1299, "på_lager": True},
                {"delnr": "MEC-67890", "navn": "Oljeilter", "pris": 349, "på_lager": True},
            ]
        })
    else:
        return jsonify({"error": "Ingen deler funnet for dette regnr"}), 404

@app.route("/api/rackbeat_parts", methods=["GET"])
def rackbeat_parts():
    try:
        headers = {
            'Authorization': f'Bearer {os.getenv("RACKBEAT_API_KEY")}',
            'Content-Type': 'application/json'
        }
        response = requests.get('https://app.rackbeat.com/api/products', headers=headers)
        response.raise_for_status()
        data = response.json()
        return jsonify(data)
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Rackbeat API error: {str(e)}"}), 500

@app.route("/api/car_parts_search", methods=["GET"])
def car_parts_search():
    regnr = request.args.get("regnr", "").upper()
    if not regnr:
        return jsonify({"error": "Missing regnr parameter"}), 400
    
    try:
        vehicle_data = {
            "regnr": regnr,
            "merke": "Nissan",
            "modell": "Qashqai",
            "år": 2018,
            "drivverk": "4x4",
            "har_mellomaksel": True
        }
        
        mecaparts_data = {
            "parts": [
                {"delnr": "MEC-12345", "navn": "Bremseklosser sett", "pris": 1299, "på_lager": True},
                {"delnr": "MEC-67890", "navn": "Oljeilter", "pris": 349, "på_lager": True}
            ]
        }
        
        headers = {
            'Authorization': f'Bearer {os.getenv("RACKBEAT_API_KEY")}',
            'Content-Type': 'application/json'
        }
        rackbeat_response = requests.get('https://app.rackbeat.com/api/products', headers=headers)
        rackbeat_data = rackbeat_response.json()
        
        matched_parts = []
        for mecapart in mecaparts_data['parts']:
            matches = []
            for rackbeat_product in rackbeat_data.get('products', [])[:50]:
                product_name = rackbeat_product.get('name', '').lower()
                mecapart_name = mecapart['navn'].lower()
                
                if ('brems' in product_name and 'brems' in mecapart_name) or ('olje' in product_name and 'olje' in mecapart_name):
                    matches.append({
                        'rackbeat_number': rackbeat_product.get('number'),
                        'rackbeat_name': rackbeat_product.get('name'),
                        'stock_quantity': rackbeat_product.get('stock_quantity', 0),
                        'in_stock': rackbeat_product.get('stock_quantity', 0) > 0
                    })
            
            matched_parts.append({
                'mecapart': mecapart,
                'rackbeat_matches': matches[:3]
            })
        
        response = {
            'search_date': datetime.now().isoformat(),
            'license_plate': regnr,
            'vehicle_info': vehicle_data,
            'compatible_parts': matched_parts,
            'summary': {
                'total_parts': len(mecaparts_data['parts']),
                'total_matches': sum(len(part['rackbeat_matches']) for part in matched_parts)
            }
        }
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)

