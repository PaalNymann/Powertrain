#!/usr/bin/env python3
"""
Add debug endpoint to backend for OEM inspection
This will be added to app.py to help debug the OEM matching issue
"""

debug_endpoint_code = '''
@app.route('/api/debug/oem_matching/<license_plate>', methods=['GET'])
def debug_oem_matching(license_plate):
    """
    Debug endpoint to inspect OEM matching process step by step
    """
    from svv_client import hent_kjoretoydata
    from rapidapi_tecdoc import get_oem_numbers_from_rapidapi_tecdoc
    from optimized_search import search_products_by_oem_optimized
    from database import SessionLocal, ProductMetafield
    from sqlalchemy import text
    
    debug_info = {
        'license_plate': license_plate,
        'steps': {}
    }
    
    try:
        # Step 1: Get vehicle data
        debug_info['steps']['1_vehicle_data'] = {'status': 'starting'}
        vehicle_data = hent_kjoretoydata(license_plate)
        
        if not vehicle_data:
            debug_info['steps']['1_vehicle_data'] = {'status': 'failed', 'error': 'No vehicle data'}
            return jsonify(debug_info)
        
        vehicle_info = extract_vehicle_info(vehicle_data)
        debug_info['steps']['1_vehicle_data'] = {
            'status': 'success',
            'vehicle_info': {
                'make': vehicle_info.get('make'),
                'model': vehicle_info.get('model'),
                'year': vehicle_info.get('year'),
                'chassis_number': vehicle_info.get('chassis_number')
            }
        }
        
        # Step 2: Get TecDoc OEMs
        debug_info['steps']['2_tecdoc_oems'] = {'status': 'starting'}
        
        try:
            tecdoc_oems = get_oem_numbers_from_rapidapi_tecdoc(
                vehicle_info['make'], 
                vehicle_info['model'], 
                int(vehicle_info['year'])
            )
            
            debug_info['steps']['2_tecdoc_oems'] = {
                'status': 'success',
                'count': len(tecdoc_oems) if tecdoc_oems else 0,
                'oems': tecdoc_oems[:20] if tecdoc_oems else []  # First 20 for inspection
            }
            
        except Exception as e:
            debug_info['steps']['2_tecdoc_oems'] = {
                'status': 'failed',
                'error': str(e)
            }
            return jsonify(debug_info)
        
        # Step 3: Check database for these OEMs
        debug_info['steps']['3_database_check'] = {'status': 'starting'}
        
        session = SessionLocal()
        try:
            # Check total metafields
            count_query = text("SELECT COUNT(*) FROM product_metafields WHERE key = 'Original_nummer'")
            total_metafields = session.execute(count_query).scalar()
            
            # Test each TecDoc OEM against database
            oem_matches = []
            for oem in (tecdoc_oems[:10] if tecdoc_oems else []):  # Test first 10
                # Test exact match
                exact_query = text("""
                    SELECT COUNT(*) FROM product_metafields 
                    WHERE key = 'Original_nummer' AND value = :oem
                """)
                exact_count = session.execute(exact_query, {'oem': oem}).scalar()
                
                # Test LIKE patterns
                like_patterns = [f"{oem},%", f"%, {oem},%", f"%, {oem}"]
                like_count = 0
                for pattern in like_patterns:
                    like_query = text("""
                        SELECT COUNT(*) FROM product_metafields 
                        WHERE key = 'Original_nummer' AND value LIKE :pattern
                    """)
                    like_count += session.execute(like_query, {'pattern': pattern}).scalar()
                
                oem_matches.append({
                    'oem': oem,
                    'exact_matches': exact_count,
                    'like_matches': like_count,
                    'total_matches': exact_count + like_count
                })
            
            debug_info['steps']['3_database_check'] = {
                'status': 'success',
                'total_metafields': total_metafields,
                'oem_matches': oem_matches,
                'total_matching_oems': sum(1 for match in oem_matches if match['total_matches'] > 0)
            }
            
        except Exception as e:
            debug_info['steps']['3_database_check'] = {
                'status': 'failed',
                'error': str(e)
            }
        finally:
            session.close()
        
        # Step 4: Test search_products_by_oem_optimized for first few OEMs
        debug_info['steps']['4_search_function'] = {'status': 'starting'}
        
        search_results = []
        for oem in (tecdoc_oems[:3] if tecdoc_oems else []):  # Test first 3
            try:
                products = search_products_by_oem_optimized(oem)
                search_results.append({
                    'oem': oem,
                    'products_found': len(products) if products else 0,
                    'sample_products': [p.get('title', 'Unknown') for p in (products[:2] if products else [])]
                })
            except Exception as e:
                search_results.append({
                    'oem': oem,
                    'error': str(e)
                })
        
        debug_info['steps']['4_search_function'] = {
            'status': 'success',
            'search_results': search_results
        }
        
        # Summary
        debug_info['summary'] = {
            'tecdoc_oems_found': len(tecdoc_oems) if tecdoc_oems else 0,
            'database_matches': debug_info['steps']['3_database_check'].get('total_matching_oems', 0),
            'search_function_works': any(r.get('products_found', 0) > 0 for r in search_results),
            'diagnosis': 'Unknown'
        }
        
        # Diagnosis
        if debug_info['summary']['tecdoc_oems_found'] == 0:
            debug_info['summary']['diagnosis'] = 'TecDoc returns no OEMs'
        elif debug_info['summary']['database_matches'] == 0:
            debug_info['summary']['diagnosis'] = 'OEM format mismatch - TecDoc OEMs not found in database'
        elif not debug_info['summary']['search_function_works']:
            debug_info['summary']['diagnosis'] = 'search_products_by_oem_optimized() function issue'
        else:
            debug_info['summary']['diagnosis'] = 'Unknown issue - need deeper investigation'
        
        return jsonify(debug_info)
        
    except Exception as e:
        debug_info['error'] = str(e)
        debug_info['traceback'] = traceback.format_exc()
        return jsonify(debug_info), 500
'''

print("🔧 DEBUG ENDPOINT CODE FOR app.py:")
print("=" * 40)
print("Add this endpoint to app.py to debug OEM matching:")
print()
print(debug_endpoint_code)
print()
print("🎯 USAGE:")
print("GET /api/debug/oem_matching/ZT41818")
print()
print("This will show step-by-step what happens in OEM matching process")
