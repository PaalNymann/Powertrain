from flask import Flask, jsonify
import requests
app = Flask(name)
@app.route("/api/febest_parts")
def febest_parts():
    try:
        login_data = {"user": "febest.api@powertrain.no", "password": "IjGx7wXJyQhZaVRV"}
        headers = {"Content-Type": "application/json"}
        response = requests.post("https://api.febest.eu/api-v2/login/", json=login_data, headers=headers)
    if response.status_code == 200:
        token = response.json()["token"]
        return jsonify({"status": "success", "token_preview": token[:20]})
    
    return jsonify({"error": "login failed"}), 500
    
except Exception as e:
    return jsonify({"error": str(e)}), 500

if name == "main":
    app.run(port=8000, debug=True)

