#!/usr/bin/env python3
"""
Enhanced OEM search with debug logging to identify the exact issue
"""

def create_debug_oem_search():
    """Create a debug version of OEM search that shows what's actually in the database"""
    
    debug_function = '''
def search_products_by_oem_debug(oem_number):
    """
    DEBUG VERSION: Search for products by OEM with extensive logging
    """
    session = SessionLocal()
    try:
        print(f"🔍 DEBUG: Searching for OEM: {oem_number}")
        
        # First, check if ANY metafields exist at all
        count_query = text("SELECT COUNT(*) FROM product_metafields WHERE key = 'Original_nummer'")
        count_result = session.execute(count_query)
        total_oem_metafields = count_result.scalar()
        print(f"📊 Total Original_nummer metafields in database: {total_oem_metafields}")
        
        if total_oem_metafields == 0:
            print("❌ CRITICAL: No Original_nummer metafields found in database!")
            print("   This explains why no products are matched - metafields are missing!")
            return []
        
        # Check what metafield keys actually exist
        keys_query = text("SELECT DISTINCT key FROM product_metafields LIMIT 10")
        keys_result = session.execute(keys_query)
        existing_keys = [row[0] for row in keys_result.fetchall()]
        print(f"📋 Existing metafield keys: {existing_keys}")
        
        # Check a few sample Original_nummer values to see format
        sample_query = text("SELECT value FROM product_metafields WHERE key = 'Original_nummer' AND value IS NOT NULL LIMIT 10")
        sample_result = session.execute(sample_query)
        sample_oems = [row[0] for row in sample_result.fetchall()]
        print(f"🔍 Sample OEM values in database: {sample_oems}")
        
        # Now try the actual search with variations
        oem_variations = [
            oem_number,
            oem_number.upper(),
            oem_number.lower(),
            oem_number.replace('A', '').replace('a', ''),  # Remove A prefix
            ''.join(oem_number.split()),  # Remove spaces
        ]
        
        print(f"🔧 Testing OEM variations: {oem_variations}")
        
        for variation in oem_variations:
            exact_query = text("SELECT COUNT(*) FROM product_metafields WHERE key = 'Original_nummer' AND value = :oem_value")
            exact_result = session.execute(exact_query, {'oem_value': variation})
            exact_count = exact_result.scalar()
            
            if exact_count > 0:
                print(f"✅ Found {exact_count} products for variation: {variation}")
                
                # Get the actual products
                products_query = text("""
                    SELECT sp.id, sp.title, sp.handle, pm.value 
                    FROM shopify_products sp
                    INNER JOIN product_metafields pm ON sp.id = pm.product_id
                    WHERE pm.key = 'Original_nummer' AND pm.value = :oem_value
                    LIMIT 5
                """)
                products_result = session.execute(products_query, {'oem_value': variation})
                products = products_result.fetchall()
                
                for product in products:
                    print(f"   Product: {product[1]} (ID: {product[0]}, OEM: {product[3]})")
                
                return [{'id': p[0], 'title': p[1], 'handle': p[2], 'matched_oem': p[3]} for p in products]
            else:
                print(f"❌ No products found for variation: {variation}")
        
        print(f"❌ No products found for any variation of OEM: {oem_number}")
        return []
        
    except Exception as e:
        print(f"❌ Error in debug OEM search: {e}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        session.close()
'''
    
    return debug_function

def main():
    print("🔧 CREATING DEBUG OEM SEARCH FUNCTION")
    print("=" * 50)
    
    debug_function = create_debug_oem_search()
    
    print("📝 Debug function created. This function will:")
    print("1. Check if ANY Original_nummer metafields exist")
    print("2. Show what metafield keys are actually in the database")
    print("3. Show sample OEM values to see the format")
    print("4. Test multiple OEM variations (with/without A prefix, case variations)")
    print("5. Show exact matches if found")
    
    print("\n🚀 NEXT STEP:")
    print("Replace the current search_products_by_oem_optimized function with this debug version")
    print("to see exactly what's in the database and why matching fails.")
    
    print(f"\n📋 DEBUG FUNCTION:")
    print(debug_function)

if __name__ == "__main__":
    main()
