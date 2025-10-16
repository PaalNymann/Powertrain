"""
Client for bilregistret.ai OE API
Fetches OEM numbers directly from Norwegian vehicle registration numbers
"""

import requests
import os
from dotenv import load_dotenv

load_dotenv()

# bilregistret.ai API configuration
BILREGISTRET_BASE_URL = os.getenv('BILREGISTRET_BASE_URL', 'https://oe.bilregistret.ai')
BILREGISTRET_EMAIL = os.getenv('BILREGISTRET_EMAIL', 'nymannpaal@gmail.com')
BILREGISTRET_PASSWORD = os.getenv('BILREGISTRET_PASSWORD', 'rBB7Xe5wd3Vb7xUatw')

# Cache for authentication token
_auth_token = None

def authenticate():
    """
    Authenticate with bilregistret.ai API and get JWT token
    Returns: JWT token string or None if authentication fails
    """
    global _auth_token
    
    try:
        login_url = f'{BILREGISTRET_BASE_URL}/auth/login'
        login_data = {
            'email': BILREGISTRET_EMAIL,
            'password': BILREGISTRET_PASSWORD
        }
        
        print(f"🔐 Authenticating with bilregistret.ai...")
        response = requests.post(login_url, json=login_data, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            _auth_token = result.get('token')
            print(f"✅ Authentication successful")
            return _auth_token
        else:
            print(f"❌ Authentication failed: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Authentication error: {e}")
        return None

def get_oem_numbers_from_bilregistret(reg_nr):
    """
    Get OEM numbers for a vehicle from bilregistret.ai API
    
    Args:
        reg_nr: Norwegian vehicle registration number (e.g. "ZT41818")
    
    Returns:
        List of OEM numbers, or empty list if no data found
    """
    global _auth_token
    
    try:
        # Authenticate if we don't have a token
        if not _auth_token:
            _auth_token = authenticate()
            if not _auth_token:
                print(f"❌ Could not authenticate with bilregistret.ai")
                return []
        
        # Get OE data for registration number
        oe_url = f'{BILREGISTRET_BASE_URL}/api/oe/{reg_nr}'
        headers = {
            'Authorization': f'Bearer {_auth_token}'
        }
        
        print(f"🔍 Getting OEM numbers from bilregistret.ai for {reg_nr}...")
        response = requests.get(oe_url, headers=headers, timeout=15)
        
        # Handle authentication errors (token expired)
        if response.status_code == 401:
            print(f"🔄 Token expired, re-authenticating...")
            _auth_token = authenticate()
            if _auth_token:
                headers['Authorization'] = f'Bearer {_auth_token}'
                response = requests.get(oe_url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            result = response.json()
            metadata = result.get('metadata', {})
            oe_numbers = result.get('data', [])
            
            vehicle_info = f"{metadata.get('C_merke')} {metadata.get('C_modell')} {metadata.get('C_typ')}"
            print(f"✅ Found {len(oe_numbers)} OEM numbers for {vehicle_info}")
            
            if len(oe_numbers) == 0:
                print(f"⚠️  bilregistret.ai has no OEM data for this vehicle")
                print(f"    This is common for:")
                print(f"    - Electric vehicles (BEV)")
                print(f"    - Plug-in hybrids (PHEV)")
                print(f"    - Newer models (2019+)")
            
            return oe_numbers
            
        elif response.status_code == 400:
            print(f"❌ Registration number not found in bilregistret.ai: {reg_nr}")
            return []
            
        elif response.status_code == 502:
            print(f"❌ bilregistret.ai upstream service error")
            return []
            
        else:
            print(f"❌ bilregistret.ai API error: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return []
            
    except requests.exceptions.Timeout:
        print(f"❌ bilregistret.ai API timeout")
        return []
        
    except Exception as e:
        print(f"❌ Error getting OEM numbers from bilregistret.ai: {e}")
        return []

def get_vehicle_metadata_from_bilregistret(reg_nr):
    """
    Get vehicle metadata (make, model, type, power) from bilregistret.ai API
    This can be used as a fallback if SVV API fails
    
    Args:
        reg_nr: Norwegian vehicle registration number
    
    Returns:
        Dictionary with vehicle metadata, or None if not found
    """
    global _auth_token
    
    try:
        # Authenticate if we don't have a token
        if not _auth_token:
            _auth_token = authenticate()
            if not _auth_token:
                return None
        
        # Get OE data for registration number
        oe_url = f'{BILREGISTRET_BASE_URL}/api/oe/{reg_nr}'
        headers = {
            'Authorization': f'Bearer {_auth_token}'
        }
        
        response = requests.get(oe_url, headers=headers, timeout=15)
        
        # Handle authentication errors
        if response.status_code == 401:
            _auth_token = authenticate()
            if _auth_token:
                headers['Authorization'] = f'Bearer {_auth_token}'
                response = requests.get(oe_url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            result = response.json()
            metadata = result.get('metadata', {})
            
            return {
                'registration': metadata.get('KJM', ''),
                'make': metadata.get('C_merke', ''),
                'model': metadata.get('C_modell', ''),
                'type': metadata.get('C_typ', ''),
                'power_kw': metadata.get('C_kw', ''),
                'power_hp': metadata.get('C_hk', '')
            }
        else:
            return None
            
    except Exception as e:
        print(f"❌ Error getting vehicle metadata: {e}")
        return None

if __name__ == '__main__':
    # Test the client
    print("Testing bilregistret.ai client...")
    print("="*60)
    
    # Test with known registration numbers
    test_cases = [
        'ZT41818',  # Nissan X-Trail - should have OEM data
        'RJ62438',  # Volvo V70 II - no OEM data
        'BT17439',  # VW Tiguan - should have OEM data
    ]
    
    for reg_nr in test_cases:
        print(f"\nTesting {reg_nr}:")
        oem_numbers = get_oem_numbers_from_bilregistret(reg_nr)
        print(f"Result: {len(oem_numbers)} OEM numbers")
        if oem_numbers:
            print(f"First 5: {oem_numbers[:5]}")
