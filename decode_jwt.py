#!/usr/bin/env python3
import jwt
import os
from dotenv import load_dotenv
import json

load_dotenv()

def decode_jwt_token():
    """Decode the JWT token to check its contents"""
    
    print("=== JWT TOKEN ANALYSIS ===")
    
    RACKBEAT_API_KEY = os.getenv('RACKBEAT_API_KEY')
    
    if not RACKBEAT_API_KEY:
        print("No RACKBEAT_API_KEY found")
        return
    
    print(f"Token: {RACKBEAT_API_KEY[:50]}...")
    
    try:
        # Decode without verification to see the payload
        decoded = jwt.decode(RACKBEAT_API_KEY, options={"verify_signature": False})
        
        print("\n=== JWT PAYLOAD ===")
        print(json.dumps(decoded, indent=2))
        
        # Check if token is expired
        import time
        current_time = time.time()
        
        if 'exp' in decoded:
            exp_time = decoded['exp']
            if current_time > exp_time:
                print(f"\n❌ TOKEN IS EXPIRED!")
                print(f"Expired at: {exp_time}")
                print(f"Current time: {current_time}")
            else:
                print(f"\n✅ TOKEN IS VALID")
                print(f"Expires at: {exp_time}")
                print(f"Current time: {current_time}")
                print(f"Time remaining: {exp_time - current_time} seconds")
        
        if 'iat' in decoded:
            print(f"Issued at: {decoded['iat']}")
            
        if 'sub' in decoded:
            print(f"Subject: {decoded['sub']}")
            
        if 'aud' in decoded:
            print(f"Audience: {decoded['aud']}")
            
    except jwt.InvalidTokenError as e:
        print(f"❌ Invalid JWT token: {e}")
    except Exception as e:
        print(f"❌ Error decoding token: {e}")

if __name__ == "__main__":
    decode_jwt_token() 