"""
Debug script to see full SVV API response for a vehicle
"""

from svv_client import hent_kjoretoydata
import json
import sys

def debug_svv_response(reg_nr):
    """Show full SVV response and extracted fields"""
    print(f'Testing SVV API for: {reg_nr}')
    print('='*60)
    
    try:
        vehicle_data = hent_kjoretoydata(reg_nr)
        
        if not vehicle_data or 'kjoretoydataListe' not in vehicle_data:
            print('❌ No vehicle data found')
            return
        
        kjoretoy = vehicle_data['kjoretoydataListe'][0]
        
        # Save full response to file for inspection
        with open(f'svv_response_{reg_nr}.json', 'w', encoding='utf-8') as f:
            json.dump(vehicle_data, f, indent=2, ensure_ascii=False)
        print(f'✅ Full response saved to: svv_response_{reg_nr}.json')
        
        # Extract key paths
        tekniske_data = kjoretoy.get('godkjenning', {}).get('tekniskGodkjenning', {}).get('tekniskeData', {})
        
        print('\n' + '='*60)
        print('CHECKING KEY FIELDS:')
        print('='*60)
        
        # 1. Akslinger (axles)
        print('\n1. AKSLINGER (Axles):')
        akslinger = tekniske_data.get('akslinger', {})
        if akslinger:
            print(f'   ✅ Found: {json.dumps(akslinger, indent=6, ensure_ascii=False)}')
            
            # Check for antal aksler
            antall_aksler = akslinger.get('antallAksler')
            print(f'   antallAksler: {antall_aksler}')
            
            # Check for aksler med drift
            aksler_med_drift = akslinger.get('akselMedDrift', [])
            print(f'   akselMedDrift: {aksler_med_drift}')
        else:
            print('   ❌ No akslinger data found')
        
        # 2. Motor og drivverk
        print('\n2. MOTOR OG DRIVVERK:')
        motor_og_drivverk = tekniske_data.get('motorOgDrivverk', {})
        if motor_og_drivverk:
            motor = motor_og_drivverk.get('motor', {})
            
            # Drivstoff
            drivstoff = motor.get('drivstoff', [])
            print(f'   drivstoff: {drivstoff}')
            
            # Effekt
            effekt = motor.get('maksEffekt')
            print(f'   maksEffekt: {effekt} kW')
            
            # Slagvolum
            slagvolum = motor.get('slagvolum')
            print(f'   slagvolum: {slagvolum} cm³')
        else:
            print('   ❌ No motorOgDrivverk data found')
        
        # 3. Show all top-level keys in tekniskeData
        print('\n3. ALL AVAILABLE KEYS IN tekniskeData:')
        for key in sorted(tekniske_data.keys()):
            value = tekniske_data[key]
            if isinstance(value, dict):
                print(f'   {key}: (dict with {len(value)} keys)')
            elif isinstance(value, list):
                print(f'   {key}: (list with {len(value)} items)')
            else:
                print(f'   {key}: {value}')
        
        print('\n' + '='*60)
        print('Check the JSON file for complete response structure')
        print('='*60)
        
    except Exception as e:
        print(f'❌ Error: {e}')
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    if len(sys.argv) > 1:
        reg_nr = sys.argv[1].upper()
    else:
        reg_nr = input('Enter registration number (e.g. AB12345): ').strip().upper()
    
    if reg_nr:
        debug_svv_response(reg_nr)
    else:
        print('No registration number provided')
