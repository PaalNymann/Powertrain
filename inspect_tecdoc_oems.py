#!/usr/bin/env python3
"""
Inspect what OEMs TecDoc actually returns for ZT41818 vs what's in our database
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from rapidapi_tecdoc import get_oem_numbers_from_rapidapi_tecdoc
from database import SessionLocal, ProductMetafield
from sqlalchemy import text

def get_tecdoc_oems_for_zt41818():
    """Get the actual OEMs that TecDoc returns for ZT41818"""
    
    print("🔍 GETTING TECDOC OEMS FOR ZT41818")
    print("=" * 40)
    
    try:
        # Call TecDoc API directly for Nissan X-Trail 2006
        print("📡 Calling TecDoc API for NISSAN X-TRAIL 2006...")
        oem_numbers = get_oem_numbers_from_rapidapi_tecdoc("NISSAN", "X-TRAIL", 2006)
        
        if oem_numbers:
            print(f"✅ TecDoc returned {len(oem_numbers)} OEM numbers:")
            for i, oem in enumerate(oem_numbers, 1):
                print(f"   {i:2d}. {oem}")
            
            return oem_numbers
        else:
            print("❌ TecDoc returned no OEM numbers")
            return []
            
    except Exception as e:
        print(f"❌ Error calling TecDoc: {e}")
        import traceback
        traceback.print_exc()
        return []

def check_database_oems():
    """Check what OEMs exist in our database"""
    
    print(f"\n🔍 CHECKING DATABASE OEMS")
    print("=" * 30)
    
    session = SessionLocal()
    try:
        # Get total count of Original_nummer metafields
        count_query = text("SELECT COUNT(*) FROM product_metafields WHERE key = 'Original_nummer'")
        count_result = session.execute(count_query)
        total_oem_metafields = count_result.scalar()
        print(f"📊 Total Original_nummer metafields: {total_oem_metafields}")
        
        # Get sample OEM values to see format
        sample_query = text("""
            SELECT pm.value, sp.title, sp.sku 
            FROM product_metafields pm
            JOIN shopify_products sp ON pm.product_id = sp.id
            WHERE pm.key = 'Original_nummer' 
            AND pm.value IS NOT NULL 
            AND pm.value != ''
            LIMIT 10
        """)
        sample_result = session.execute(sample_query)
        samples = sample_result.fetchall()
        
        print(f"\n📋 Sample OEM values in database:")
        for i, (oem_value, title, sku) in enumerate(samples, 1):
            print(f"   {i:2d}. {sku}: {oem_value[:50]}{'...' if len(oem_value) > 50 else ''}")
            print(f"       Product: {title[:60]}{'...' if len(title) > 60 else ''}")
        
        return samples
        
    except Exception as e:
        print(f"❌ Error checking database: {e}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        session.close()

def check_nissan_oems_in_database():
    """Check if known Nissan OEMs exist in database"""
    
    print(f"\n🔍 CHECKING KNOWN NISSAN OEMS IN DATABASE")
    print("=" * 45)
    
    # Customer-verified Nissan OEMs for MA18002
    known_nissan_oems = [
        "370008H310",
        "370008H510", 
        "370008H800",
        "37000-8H310",
        "37000-8H510",
        "37000-8H800"
    ]
    
    session = SessionLocal()
    try:
        for oem in known_nissan_oems:
            print(f"\n🔍 Searching for OEM: {oem}")
            
            # Search with various patterns
            patterns = [
                f"{oem}",           # Exact match
                f"{oem},%",         # At start of list
                f"%, {oem},%",      # In middle of list  
                f"%, {oem}",        # At end of list
            ]
            
            found = False
            for pattern in patterns:
                if pattern == oem:
                    # Exact match
                    query = text("""
                        SELECT pm.value, sp.title, sp.sku 
                        FROM product_metafields pm
                        JOIN shopify_products sp ON pm.product_id = sp.id
                        WHERE pm.key = 'Original_nummer' 
                        AND pm.value = :pattern
                        LIMIT 3
                    """)
                else:
                    # LIKE pattern
                    query = text("""
                        SELECT pm.value, sp.title, sp.sku 
                        FROM product_metafields pm
                        JOIN shopify_products sp ON pm.product_id = sp.id
                        WHERE pm.key = 'Original_nummer' 
                        AND pm.value LIKE :pattern
                        LIMIT 3
                    """)
                
                result = session.execute(query, {'pattern': pattern})
                matches = result.fetchall()
                
                if matches:
                    found = True
                    print(f"   ✅ Found {len(matches)} matches with pattern: {pattern}")
                    for oem_value, title, sku in matches:
                        print(f"      {sku}: {title[:50]}{'...' if len(title) > 50 else ''}")
                        print(f"      OEMs: {oem_value}")
                    break
            
            if not found:
                print(f"   ❌ OEM {oem} not found in database")
        
    except Exception as e:
        print(f"❌ Error checking Nissan OEMs: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

def compare_tecdoc_vs_database(tecdoc_oems):
    """Compare TecDoc OEMs with database OEMs to find format differences"""
    
    print(f"\n🔍 COMPARING TECDOC VS DATABASE OEMS")
    print("=" * 40)
    
    if not tecdoc_oems:
        print("❌ No TecDoc OEMs to compare")
        return
    
    session = SessionLocal()
    try:
        print(f"📊 Testing {len(tecdoc_oems)} TecDoc OEMs against database...")
        
        matches_found = 0
        for i, oem in enumerate(tecdoc_oems, 1):
            print(f"\n{i:2d}. Testing OEM: {oem}")
            
            # Test exact match first
            exact_query = text("""
                SELECT COUNT(*) FROM product_metafields 
                WHERE key = 'Original_nummer' 
                AND value = :oem
            """)
            exact_result = session.execute(exact_query, {'oem': oem})
            exact_count = exact_result.scalar()
            
            if exact_count > 0:
                print(f"    ✅ EXACT MATCH: {exact_count} products")
                matches_found += 1
                continue
            
            # Test LIKE patterns
            like_patterns = [
                f"{oem},%",         # At start
                f"%, {oem},%",      # In middle
                f"%, {oem}",        # At end
            ]
            
            total_like_matches = 0
            for pattern in like_patterns:
                like_query = text("""
                    SELECT COUNT(*) FROM product_metafields 
                    WHERE key = 'Original_nummer' 
                    AND value LIKE :pattern
                """)
                like_result = session.execute(like_query, {'pattern': pattern})
                like_count = like_result.scalar()
                total_like_matches += like_count
            
            if total_like_matches > 0:
                print(f"    ✅ LIKE MATCH: {total_like_matches} products")
                matches_found += 1
            else:
                print(f"    ❌ NO MATCH")
        
        print(f"\n📊 SUMMARY:")
        print(f"   TecDoc OEMs: {len(tecdoc_oems)}")
        print(f"   Database matches: {matches_found}")
        print(f"   Match rate: {matches_found/len(tecdoc_oems)*100:.1f}%")
        
        if matches_found == 0:
            print(f"\n❌ CRITICAL: No TecDoc OEMs match database!")
            print(f"   This explains why ZT41818 returns 0 products")
            print(f"   Need to check OEM format normalization")
        elif matches_found < len(tecdoc_oems):
            print(f"\n⚠️  PARTIAL MATCH: Some TecDoc OEMs don't match database")
            print(f"   This may explain reduced product count")
        else:
            print(f"\n✅ FULL MATCH: All TecDoc OEMs found in database")
            print(f"   The issue may be elsewhere in the matching logic")
        
    except Exception as e:
        print(f"❌ Error comparing OEMs: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    print("🔍 INSPECTING TECDOC VS DATABASE OEMS FOR ZT41818")
    print("=" * 55)
    
    # Get TecDoc OEMs
    tecdoc_oems = get_tecdoc_oems_for_zt41818()
    
    # Check database OEMs
    check_database_oems()
    
    # Check known Nissan OEMs
    check_nissan_oems_in_database()
    
    # Compare TecDoc vs database
    compare_tecdoc_vs_database(tecdoc_oems)
    
    print(f"\n🎯 NEXT STEPS:")
    if tecdoc_oems:
        print(f"   1. If no matches found: Fix OEM normalization")
        print(f"   2. If partial matches: Debug format differences")
        print(f"   3. If full matches: Debug search_products_by_oem_optimized() logic")
    else:
        print(f"   1. Fix TecDoc API call for Nissan X-Trail")
        print(f"   2. Check if requests module works in local environment")
