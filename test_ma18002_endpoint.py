#!/usr/bin/env python3
"""
Simple endpoint test to check MA18002 via sync service
This can be deployed to Railway to test actual Rackbeat data
"""

# Add this endpoint to sync_service.py for testing:

TEST_ENDPOINT_CODE = '''
@app.route('/test/ma18002', methods=['GET'])
def test_ma18002():
    """Test endpoint to check MA18002 specifically"""
    try:
        # Get all products from Rackbeat
        headers = get_rackbeat_headers()
        url = "https://app.rackbeat.com/api/products"
        
        # Search for MA18002 specifically
        params = {"search": "MA18002", "per_page": 100}
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code != 200:
            return jsonify({"error": f"Rackbeat API error: {response.status_code}"}), 500
        
        data = response.json()
        products = data.get('data', [])
        
        # Find MA18002
        ma18002 = None
        for product in products:
            if product.get('number') == 'MA18002':
                ma18002 = product
                break
        
        if not ma18002:
            return jsonify({
                "found": False,
                "message": f"MA18002 not found in {len(products)} products",
                "all_products": [p.get('number') for p in products[:10]]  # First 10 for reference
            })
        
        # Test filter logic
        should_sync = filter_keep(ma18002)
        
        # Extract key fields
        group_name = ma18002.get('group', {}).get('name', 'NO_GROUP')
        stock = ma18002.get('available_quantity', 0)
        price = ma18002.get('sales_price', 0)
        i_nettbutikk = get_i_nettbutikk_from_metadata(ma18002.get('metadata', []))
        
        # Debug metadata
        metadata_debug = []
        for item in ma18002.get('metadata', []):
            metadata_debug.append({
                "slug": item.get('slug'),
                "value": item.get('value')
            })
        
        return jsonify({
            "found": True,
            "number": ma18002.get('number'),
            "name": ma18002.get('name'),
            "group": group_name,
            "stock": stock,
            "price": price,
            "i_nettbutikk": i_nettbutikk,
            "should_sync": should_sync,
            "metadata": metadata_debug,
            "filter_results": {
                "group_ok": group_name in ['Drivaksel', 'Mellomaksel'],
                "stock_ok": stock >= 1,
                "price_ok": price > 0,
                "i_nettbutikk_ok": i_nettbutikk == 'ja'
            }
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
'''

print("🔍 TEST ENDPOINT FOR MA18002")
print("=" * 50)
print()
print("📋 DEPLOYMENT INSTRUCTIONS:")
print("1. Add this endpoint to sync_service.py")
print("2. Deploy to Railway")
print("3. Call GET /test/ma18002")
print("4. Check response for MA18002 details")
print()
print("🎯 WHAT TO LOOK FOR:")
print("- found: true/false")
print("- group: should be 'Mellomaksel'")
print("- stock: should be > 0")
print("- price: should be > 0")
print("- i_nettbutikk: should be 'ja'")
print("- should_sync: should be true")
print()
print("📄 ENDPOINT CODE TO ADD:")
print(TEST_ENDPOINT_CODE)
