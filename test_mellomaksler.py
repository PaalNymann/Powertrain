#!/usr/bin/env python3
"""
Test script to verify Mellomaksler product group works for Nissan X-Trail
Target: Find OEM 370008H310 for customer-verified part MA18002
"""

import os
import sys

# Set up environment
os.environ['RAPIDAPI_KEY'] = '48a6ede874mshe38f052cb6a6109p12916fjsn0d0c0912c5ed'

from rapidapi_tecdoc import get_oem_numbers_from_rapidapi_tecdoc

def test_nissan_xtrail_mellomaksler():
    """Test if we can find customer-verified OEMs for Nissan X-Trail"""
    
    print('🧪 TESTING MELLOMAKSLER PRODUKTGRUPPE FOR NISSAN X-TRAIL...')
    print('Target: Find OEM 370008H310 for MA18002')
    print('=' * 60)
    
    # Test Nissan X-Trail 2006 (ZT41818)
    brand = 'NISSAN'
    model = 'X-TRAIL'
    year = 2006
    
    print(f'🔍 Testing: {brand} {model} {year}')
    print('Expected: Should now find OEM 370008H310 in Mellomaksler group')
    print()
    
    try:
        oem_numbers = get_oem_numbers_from_rapidapi_tecdoc(brand, model, year)
        
        print(f'📊 RESULTS:')
        print(f'Total OEM numbers found: {len(oem_numbers)}')
        
        # Check for customer-verified OEMs
        target_oems = [
            '37000-8H310', '37000-8H510', '37000-8H800', 
            '370008H310', '370008H510', '370008H800'
        ]
        
        found_oems = []
        for oem in target_oems:
            if oem in oem_numbers:
                found_oems.append(oem)
                print(f'✅ FOUND customer-verified OEM: {oem}')
        
        if found_oems:
            print(f'\n🎯 SUCCESS! Found {len(found_oems)} customer-verified OEMs!')
            print(f'This means MA18002 should now appear for ZT41818!')
            return True
        else:
            print(f'\n❌ No customer-verified OEMs found')
            print(f'Need to debug further...')
            
        # Show first 10 OEMs for debugging
        print(f'\n📋 First 10 OEMs found:')
        for i, oem in enumerate(oem_numbers[:10]):
            print(f'   {i+1}. {oem}')
            
        return len(found_oems) > 0
        
    except Exception as e:
        print(f'❌ Error: {e}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_nissan_xtrail_mellomaksler()
    
    if success:
        print('\n🚀 READY FOR PRODUCTION DEPLOYMENT!')
        print('The fix should make MA18002 appear for ZT41818')
    else:
        print('\n⚠️ NEED MORE DEBUGGING')
        print('May need to check TecDoc product group IDs')
    
    sys.exit(0 if success else 1)
