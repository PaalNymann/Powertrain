#!/usr/bin/env python3
import requests
import os
from dotenv import load_dotenv

load_dotenv()

# Get environment variables
SVV_API_KEY = os.getenv("SVV_API_KEY")
CLIENT_ID = os.getenv("CLIENT_ID")
SCOPE = os.getenv("SCOPE")

print(f"Analyzing Statens Vegvesen authentication...")
print(f"API Key: {SVV_API_KEY[:50]}...")
print(f"Client ID: {CLIENT_ID}")
print(f"Scope: {SCOPE}")

# The API key looks like a JWT token, let's decode it to see if it's expired
import jwt
import base64

try:
    # Try to decode the JWT token (without verification)
    parts = SVV_API_KEY.split('.')
    if len(parts) == 3:
        # Decode the payload part
        payload_part = parts[1]
        # Add padding if needed
        padding = 4 - len(payload_part) % 4
        if padding != 4:
            payload_part += '=' * padding
        
        payload_bytes = base64.urlsafe_b64decode(payload_part)
        payload = jwt.decode(SVV_API_KEY, options={"verify_signature": False})
        
        print(f"\nJWT Token Analysis:")
        print(f"Issued at: {payload.get('iat')}")
        print(f"Expires at: {payload.get('exp')}")
        print(f"Subject: {payload.get('sub')}")
        print(f"Audience: {payload.get('aud')}")
        print(f"Scopes: {payload.get('scopes', [])}")
        
        # Check if token is expired
        import time
        current_time = int(time.time())
        if 'exp' in payload and payload['exp'] < current_time:
            print(f"❌ Token is EXPIRED! (expired at {payload['exp']}, current time {current_time})")
        else:
            print(f"✅ Token is still valid")
            
    else:
        print("Not a valid JWT token format")
        
except Exception as e:
    print(f"Error decoding JWT: {e}")

# Test if we can get a new token
print(f"\n--- Testing token endpoint ---")
token_url = "https://akfell-datautlevering.atlas.vegvesen.no/oauth/token"
try:
    response = requests.get(token_url, timeout=30)
    print(f"Token endpoint status: {response.status_code}")
    print(f"Response: {response.text[:200]}")
except Exception as e:
    print(f"Error accessing token endpoint: {e}") 