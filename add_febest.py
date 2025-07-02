with open('app.py', 'a') as f:
    f.write('''
@app.route("/api/febest_parts", methods=["GET"])
def febest_parts():
    try:
        login_data = {"user": "febest.api@powertrain.no", "password": "IjGx7wXJyQhZaVRV"}
        headers = {"Content-Type": "application/json"}
        response = requests.post("https://api.febest.eu/api-v2/login/", json=login_data, headers=headers)
    if response.status_code == 200:
        token = response.json()["token"]
        return jsonify({"status": "success", "token_preview": token[:20] + "..."})
    
    return jsonify({"error": "Febest login failed"}), 500
    
except Exception as e:
    return jsonify({"error": f"Febest API error: {str(e)}"}, 500

''')
