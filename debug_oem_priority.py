#!/usr/bin/env python3
"""
Debug OEM Priority for YZ99554
Check which OEMs are being tested and why MA01002 is not found
"""

import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = 'postgresql://postgres:pmTNRdLNPAwZTYvtBFsqvfmjUOoNEuqM@shinkansen.proxy.rlwy.net:13074/railway'

def check_oem_priority():
    """Check which OEMs are being tested first and where MA01002 ranks"""
    print("🔍 CHECKING OEM PRIORITY FOR YZ99554")
    print("=" * 50)
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # Get the first 30 OEMs that would be tested (API limits to 20)
        print("📋 Getting first 30 OEMs from database (API tests first 20)...")
        
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
            LIMIT 30
        """)
        
        results = cursor.fetchall()
        
        print(f"📦 Found {len(results)} OEM entries:")
        print(f"🎯 Looking for MA01002 OEMs: A2044102401, A2044106901, 2044102401, etc.")
        
        ma01002_oems = [
            "A2044102401", "A2044106901", "2044102401", "2044106901", 
            "A2044106701", "2044106701", "A2044101801", "2044101801", 
            "A2044102601", "2044102601", "A2214101701", "2214101701"
        ]
        
        ma01002_found_in_first_20 = False
        
        for i, (oem_value, product_id, title) in enumerate(results):
            # Parse comma-separated OEMs
            oem_list = [oem.strip() for oem in oem_value.split(',') if oem.strip()]
            
            # Check if any MA01002 OEMs are in this entry
            ma01002_match = any(ma_oem in oem_list for ma_oem in ma01002_oems)
            
            status = "🎯 MA01002!" if product_id == "MA01002" else "📦"
            priority = "🔥 TESTED" if i < 20 else "⏸️  NOT TESTED"
            
            print(f"{i+1:2d}. {status} {priority} {product_id} - {title[:40]}...")
            
            if ma01002_match:
                matching_oems = [oem for oem in oem_list if oem in ma01002_oems]
                print(f"     🔍 Contains MA01002 OEMs: {matching_oems}")
                
                if i < 20:
                    ma01002_found_in_first_20 = True
            
            # Show first few OEMs
            if len(oem_list) > 0:
                preview_oems = oem_list[:3]
                if len(oem_list) > 3:
                    preview_oems.append(f"... +{len(oem_list)-3} more")
                print(f"     📋 OEMs: {', '.join(preview_oems)}")
        
        print(f"\n📊 ANALYSIS:")
        print(f"🔍 MA01002 OEMs in first 20 tested: {'✅ YES' if ma01002_found_in_first_20 else '❌ NO'}")
        
        if not ma01002_found_in_first_20:
            print(f"🎯 SOLUTION: Increase API OEM limit or prioritize MA01002 OEMs")
        
        # Check specifically for MA01002
        print(f"\n🔍 CHECKING MA01002 SPECIFICALLY:")
        cursor.execute("""
            SELECT pm.key, pm.value 
            FROM product_metafields pm 
            WHERE pm.product_id = 'MA01002'
            ORDER BY pm.key
        """)
        
        ma01002_metafields = cursor.fetchall()
        if ma01002_metafields:
            print(f"✅ MA01002 found in database:")
            for key, value in ma01002_metafields:
                print(f"   {key}: {value}")
        else:
            print(f"❌ MA01002 NOT FOUND in database!")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_oem_priority()
