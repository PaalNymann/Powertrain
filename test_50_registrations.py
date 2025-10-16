"""
Test 50 Norwegian registration numbers with bilregistret.ai API
Report which ones return empty results (0 OEM numbers)
"""

import requests
import json
import time

BASE_URL = 'https://oe.bilregistret.ai'
EMAIL = 'nymannpaal@gmail.com'
PASSWORD = 'rBB7Xe5wd3Vb7xUatw'

# Real Norwegian registration numbers from finn.no
# 20 Volvo V70 + 30 other Volvo models
test_registrations = [
    # Volvo V70 (20 stk)
    'RA42675', 'BS17291', 'NV47302', 'JV20106', 'HF24653',
    'HJ74528', 'DL91007', 'AE42364', 'AE33224', 'JV14817',
    'AY23187', 'BT16324', 'FT51760', 'DN94146', 'BR70925',
    'NF61402', 'RZ24893', 'BS53383', 'JD57083', 'KH17495',
    
    # Other Volvo models (30 stk)
    'EH27496', 'EH84936', 'EJ96334', 'BU20581', 'SX21478',
    'HJ99478', 'SV78216', 'KJ36035', 'RL64855', 'NH10665',
    'RL64858', 'DS17440', 'CX10970', 'DS17306', 'ZZ29802',
    'DS16196', 'BU32750', 'NE13071', 'DS14748', 'DP67257',
    'FT71884', 'BT78995', 'LS95673', 'LS96225', 'ED64763',
    'ED70531', 'ED42366', 'LS95501', 'LS97120', 'EE31865'
]

print('Testing 50 Norwegian registration numbers with bilregistret.ai')
print('='*80)

# Login
print('\nAuthenticating...')
try:
    login_response = requests.post(
        f'{BASE_URL}/auth/login',
        json={'email': EMAIL, 'password': PASSWORD},
        timeout=10
    )
    
    if login_response.status_code != 200:
        print(f'❌ Login failed: {login_response.status_code}')
        exit(1)
    
    token = login_response.json().get('token')
    print('✅ Authenticated successfully\n')
    
except Exception as e:
    print(f'❌ Login error: {e}')
    exit(1)

# Test each registration number
headers = {'Authorization': f'Bearer {token}'}
results = {
    'successful': [],
    'empty': [],
    'not_found': [],
    'errors': []
}

print(f'Testing {len(test_registrations)} registration numbers...\n')

for idx, reg_nr in enumerate(test_registrations, 1):
    print(f'[{idx:2d}/50] Testing {reg_nr}...', end=' ')
    
    try:
        oe_response = requests.get(
            f'{BASE_URL}/api/oe/{reg_nr}',
            headers=headers,
            timeout=15
        )
        
        if oe_response.status_code == 200:
            result = oe_response.json()
            metadata = result.get('metadata', {})
            oe_numbers = result.get('data', [])
            
            if len(oe_numbers) > 0:
                results['successful'].append({
                    'reg_nr': reg_nr,
                    'make': metadata.get('C_merke'),
                    'model': metadata.get('C_modell'),
                    'oe_count': len(oe_numbers)
                })
                print(f'✅ {metadata.get("C_merke")} {metadata.get("C_modell")} - {len(oe_numbers)} OEM numbers')
            else:
                results['empty'].append({
                    'reg_nr': reg_nr,
                    'make': metadata.get('C_merke'),
                    'model': metadata.get('C_modell'),
                    'type': metadata.get('C_typ')
                })
                print(f'⚠️  {metadata.get("C_merke")} {metadata.get("C_modell")} - 0 OEM numbers (EMPTY)')
                
        elif oe_response.status_code == 400:
            results['not_found'].append(reg_nr)
            print('❌ Not found in registry')
        else:
            results['errors'].append({
                'reg_nr': reg_nr,
                'status': oe_response.status_code,
                'error': oe_response.text[:100]
            })
            print(f'❌ Error {oe_response.status_code}')
            
    except Exception as e:
        results['errors'].append({
            'reg_nr': reg_nr,
            'error': str(e)[:100]
        })
        print(f'❌ Exception: {str(e)[:50]}')
    
    # Small delay to avoid rate limiting
    time.sleep(0.5)

# Print summary
print('\n' + '='*80)
print('SUMMARY')
print('='*80)

print(f'\n✅ Successful (with OEM numbers): {len(results["successful"])}')
if results['successful']:
    for r in results['successful'][:10]:
        print(f'   - {r["reg_nr"]}: {r["make"]} {r["model"]} ({r["oe_count"]} OEM numbers)')
    if len(results['successful']) > 10:
        print(f'   ... and {len(results["successful"]) - 10} more')

print(f'\n⚠️  Empty results (0 OEM numbers): {len(results["empty"])}')
if results['empty']:
    print('\n   THESE VEHICLES NEED ATTENTION:')
    for r in results['empty']:
        print(f'   - {r["reg_nr"]}: {r["make"]} {r["model"]} {r["type"]}')

print(f'\n❌ Not found in registry: {len(results["not_found"])}')
if results['not_found']:
    for reg_nr in results['not_found'][:10]:
        print(f'   - {reg_nr}')

print(f'\n❌ Errors: {len(results["errors"])}')
if results['errors']:
    for err in results['errors'][:5]:
        print(f'   - {err["reg_nr"]}: {err.get("error", err.get("status"))}')

# Save detailed results to JSON file
output_file = 'test_50_results.json'
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print(f'\n📄 Detailed results saved to: {output_file}')

# Calculate success rate
total_valid = len(results['successful']) + len(results['empty'])
if total_valid > 0:
    success_rate = (len(results['successful']) / total_valid) * 100
    print(f'\n📊 Data coverage: {success_rate:.1f}% of valid vehicles have OEM data')

print('\nDone!')
