#!/usr/bin/env python3
"""
Test if MA18002 exists in database and what OEMs it has
Then test if TecDoc OEMs can match these database OEMs
"""

import requests
import json

BACKEND_URL = "https://web-production-0809b.up.railway.app"

def create_ma18002_test_endpoint():
    """Create endpoint to test MA18002 directly in database"""
    
    endpoint_code = '''
@app.route('/api/test/ma18002', methods=['GET'])
def test_ma18002():
    """
    Test if MA18002 exists in database and show its OEMs
    """
    from database import SessionLocal, ProductMetafield, ShopifyProduct
    from sqlalchemy import text
    import traceback
    
    result = {
        'ma18002_search': {},
        'nissan_oem_search': {},
        'summary': {}
    }
    
    session = SessionLocal()
    try:
        # Search for MA18002 by SKU/ID
        ma18002_query = text("""
            SELECT sp.id, sp.title, sp.sku, sp.price, sp.inventory_quantity
            FROM shopify_products sp
            WHERE sp.sku = 'MA18002' OR sp.id = 'MA18002'
            LIMIT 5
        """)
        ma18002_results = session.execute(ma18002_query).fetchall()
        
        result['ma18002_search'] = {
            'found': len(ma18002_results),
            'products': []
        }
        
        for row in ma18002_results:
            product_info = {
                'id': row[0],
                'title': row[1],
                'sku': row[2],
                'price': row[3],
                'inventory': row[4]
            }
            
            # Get metafields for this product
            metafields_query = text("""
                SELECT key, value
                FROM product_metafields
                WHERE product_id = :product_id
            """)
            metafields = session.execute(metafields_query, {'product_id': row[0]}).fetchall()
            product_info['metafields'] = {key: value for key, value in metafields}
            
            result['ma18002_search']['products'].append(product_info)
        
        # Search for known Nissan OEMs in database
        nissan_oems = ['37000-8H310', '37000-8H510', '37000-8H800', '370008H310', '370008H510', '370008H800']
        
        result['nissan_oem_search'] = {
            'tested_oems': nissan_oems,
            'matches': []
        }
        
        for oem in nissan_oems:
            # Test exact and LIKE patterns
            patterns = [
                ('exact', oem),
                ('start', f'{oem},%'),
                ('middle', f'%, {oem},%'),
                ('end', f'%, {oem}')
            ]
            
            for pattern_type, pattern in patterns:
                if pattern_type == 'exact':
                    oem_query = text("""
                        SELECT sp.id, sp.title, sp.sku, pm.value
                        FROM shopify_products sp
                        JOIN product_metafields pm ON sp.id = pm.product_id
                        WHERE pm.key = 'Original_nummer' AND pm.value = :pattern
                        LIMIT 3
                    """)
                else:
                    oem_query = text("""
                        SELECT sp.id, sp.title, sp.sku, pm.value
                        FROM shopify_products sp
                        JOIN product_metafields pm ON sp.id = pm.product_id
                        WHERE pm.key = 'Original_nummer' AND pm.value LIKE :pattern
                        LIMIT 3
                    """)
                
                oem_results = session.execute(oem_query, {'pattern': pattern}).fetchall()
                
                if oem_results:
                    result['nissan_oem_search']['matches'].append({
                        'oem': oem,
                        'pattern_type': pattern_type,
                        'pattern': pattern,
                        'matches': len(oem_results),
                        'products': [{'id': r[0], 'title': r[1], 'sku': r[2], 'oems': r[3]} for r in oem_results]
                    })
                    break  # Found match, no need to test other patterns
        
        # Summary
        result['summary'] = {
            'ma18002_exists': len(ma18002_results) > 0,
            'nissan_oems_found': len(result['nissan_oem_search']['matches']),
            'diagnosis': 'Unknown'
        }
        
        if not result['summary']['ma18002_exists']:
            result['summary']['diagnosis'] = 'MA18002 not synced to Shopify database'
        elif result['summary']['nissan_oems_found'] == 0:
            result['summary']['diagnosis'] = 'MA18002 exists but OEMs not found - sync issue'
        else:
            result['summary']['diagnosis'] = 'MA18002 and OEMs exist - matching logic issue'
        
        return jsonify(result)
        
    except Exception as e:
        result['error'] = str(e)
        result['traceback'] = traceback.format_exc()
        return jsonify(result), 500
    finally:
        session.close()
'''
    
    print("🔧 Add this endpoint to app.py:")
    print(endpoint_code)
    return endpoint_code

if __name__ == "__main__":
    print("🔍 CREATING MA18002 DATABASE TEST ENDPOINT")
    print("=" * 45)
    
    endpoint_code = create_ma18002_test_endpoint()
    
    print(f"\n🎯 This endpoint will:")
    print(f"   1. Search for MA18002 in shopify_products table")
    print(f"   2. Show its metafields (including Original_nummer)")
    print(f"   3. Test known Nissan OEMs against database")
    print(f"   4. Diagnose if issue is sync or matching logic")
    
    print(f"\n💡 Expected results:")
    print(f"   - If MA18002 exists: sync is working")
    print(f"   - If Nissan OEMs found: matching should work")
    print(f"   - If both exist but search fails: logic bug in search function")
