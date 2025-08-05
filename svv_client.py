import os
import json
import logging
import requests
import time
from jose import jwt
from cryptography.hazmat.primitives import serialization
from typing import Dict
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_maskinporten_token():
    """Get access token from Maskinporten using Buypass certificate"""
    load_dotenv()
    
    # Get environment variables
    client_id = os.getenv('CLIENT_ID')
    scope = os.getenv('SCOPE')
    token_endpoint = os.getenv('MASKINPORTEN_TOKEN_ENDPOINT')
    
    if not all([client_id, scope, token_endpoint]):
        raise EnvironmentError('Missing required Maskinporten configuration')
    
    logger.info("Getting Maskinporten token using JWT")
    
    try:
        # Load private key
        with open('private_key.pem', 'rb') as f:
            private_key_data = f.read()
        
        # JWT payload
        payload = {
            'aud': 'https://maskinporten.no/',
            'iss': client_id,
            'scope': scope,
            'iat': int(time.time()),
            'exp': int(time.time()) + 120,
            'jti': str(int(time.time()))
        }
        
        # Generate JWT with kid header
        headers = {
            'kid': client_id  # Use client_id as key identifier
        }
        client_assertion = jwt.encode(payload, private_key_data, algorithm='RS256', headers=headers)
        logger.info(f"Generated JWT with payload: {payload}")
        logger.info(f"JWT length: {len(client_assertion)}")
        
        # Request token
        token_data = {
            'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
            'assertion': client_assertion
        }
        
        logger.info(f"Token request data: {token_data}")
        
        response = requests.post(
            token_endpoint,
            data=token_data,
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )
        
        if response.status_code != 200:
            logger.error(f"Maskinporten response: {response.status_code} - {response.text}")
        
        response.raise_for_status()
        
        token_response = response.json()
        access_token = token_response.get('access_token')
        logger.info("Successfully obtained Maskinporten token")
        return access_token
        
    except Exception as e:
        logger.error(f"Failed to get Maskinporten token: {e}")
        raise


def hent_kjoretoydata(kjennemerke: str) -> Dict:
    """Hent kjøretøydata fra Statens Vegvesen basert på kjennemerke."""
    load_dotenv()
    
    try:
        # Get access token from Maskinporten
        access_token = get_maskinporten_token()
        
        # SVV endpoint
        svv_endpoint = os.getenv('SVV_KJORETOY_ENDPOINT')
        if not svv_endpoint:
            raise EnvironmentError('Missing SVV_KJORETOY_ENDPOINT')
        
        logger.info(f"Calling SVV API {svv_endpoint} with kjennemerke={kjennemerke}")
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        params = {'kjennemerke': kjennemerke}
        
        response = requests.get(
            svv_endpoint,
            params=params,
            headers=headers,
            timeout=30
        )
        
        response.raise_for_status()
        logger.info("Successfully retrieved vehicle data from SVV")
        
        return response.json()
        
    except Exception as e:
        logger.error(f"Failed to get vehicle data: {e}")
        raise 