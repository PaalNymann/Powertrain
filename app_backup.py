from flask import Flask, request, jsonify

app = Flask(__name__)

# --- Simulert Statens Vegvesen ---
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

# --- Simulert Mecaparts ---
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

# --- Simulert Rackbeat ---
@app.route("/api/rackbeat_parts", methods=["GET"])
def rackbeat_parts():
    regnr = request.args.get("regnr", "").upper()
    if regnr == "KB44781":
        return jsonify({
            "parts": [
                {"delnr": "RACK-11111", "navn": "Mellomaksel komplett", "pris": 4599, "på_lager": True},
                {"delnr": "RACK-22222", "navn": "Drivaksel venstre", "pris": 3899, "på_lager": False},
            ]
        })
    else:
        return jsonify({"error": "Ingen Rackbeat-deler funnet for dette regnr"}), 404

if __name__ == "__main__":
    app.run(debug=True)

