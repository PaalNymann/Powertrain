#!/usr/bin/env python3
"""
Find MA01002 Position in OEM Ranking
Check exactly where MA01002 appears in the alphabetically sorted OEM list
"""

import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = 'postgresql://postgres:pmTNRdLNPAwZTYvtBFsqvfmjUOoNEuqM@shinkansen.proxy.rlwy.net:13074/railway'

def find_ma01002_position():
    """Find exactly where MA01002 appears in the OEM ranking"""
    print("🔍 FINDING MA01002 POSITION IN OEM RANKING")
    print("=" * 50)
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # Get ALL OEMs sorted alphabetically (same as API does)
        print("📋 Getting ALL OEMs from database (sorted alphabetically)...")
        
        cursor.execute("""
            SELECT DISTINCT pm_oem.value, sp.id, sp.title
            FROM product_metafields pm_oem
            INNER JOIN product_metafields pm_group 
                ON pm_oem.product_id = pm_group.product_id
            INNER JOIN shopify_products sp
                ON pm_oem.product_id = sp.id
            WHERE pm_group.key = 'product_group' 
                AND pm_group.value IN ('Drivaksel', 'Mellomaksel')
                AND pm_oem.key = 'Original_nummer'
                AND pm_oem.value IS NOT NULL 
                AND pm_oem.value != ''
                AND pm_oem.value != 'N/A'
            ORDER BY pm_oem.value
        """)
        
        results = cursor.fetchall()
        
        print(f"📦 Found {len(results)} total OEM entries")
        
        ma01002_oems = [
            "A2044102401", "A2044106901", "2044102401", "2044106901", 
            "A2044106701", "2044106701", "A2044101801", "2044101801", 
            "A2044102601", "2044102601", "A2214101701", "2214101701"
        ]
        
        ma01002_position = None
        
        for i, (oem_value, product_id, title) in enumerate(results):
            # Parse comma-separated OEMs
            oem_list = [oem.strip() for oem in oem_value.split(',') if oem.strip()]
            
            # Check if this is MA01002
            if product_id == "MA01002":
                ma01002_position = i + 1
                print(f"\n🎯 FOUND MA01002 AT POSITION {ma01002_position}!")
                print(f"   📦 Product: {product_id} - {title}")
                print(f"   📋 OEMs: {oem_value[:100]}...")
                
                if ma01002_position <= 20:
                    print(f"   ✅ WITHIN FIRST 20 - Should be tested with limit=20")
                elif ma01002_position <= 50:
                    print(f"   🔥 WITHIN FIRST 50 - Should be tested with limit=50")
                else:
                    print(f"   ❌ BEYOND FIRST 50 - Will NOT be tested even with limit=50")
                
                break
            
            # Check if any MA01002 OEMs are in this entry
            ma01002_match = any(ma_oem in oem_list for ma_oem in ma01002_oems)
            if ma01002_match:
                matching_oems = [oem for oem in oem_list if oem in ma01002_oems]
                print(f"{i+1:3d}. 🔍 Contains MA01002 OEMs: {product_id} - {matching_oems}")
        
        if ma01002_position is None:
            print(f"\n❌ MA01002 NOT FOUND in OEM ranking!")
            
            # Check if MA01002 exists at all
            cursor.execute("""
                SELECT pm.key, pm.value 
                FROM product_metafields pm 
                WHERE pm.product_id = 'MA01002'
                ORDER BY pm.key
            """)
            
            ma01002_metafields = cursor.fetchall()
            if ma01002_metafields:
                print(f"\n✅ MA01002 exists in database:")
                for key, value in ma01002_metafields:
                    print(f"   {key}: {value}")
                    
                print(f"\n🤔 MA01002 might not meet the filtering criteria:")
                print(f"   - product_group must be 'Drivaksel' or 'Mellomaksel'")
                print(f"   - Original_nummer must not be NULL, empty, or 'N/A'")
            else:
                print(f"\n❌ MA01002 does not exist in database at all!")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    find_ma01002_position()
