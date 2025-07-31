#!/usr/bin/env python3
import os
from dotenv import load_dotenv

load_dotenv()

print("=== ENVIRONMENT VARIABLES TEST ===")
print(f"RACKBEAT_API_KEY: {os.getenv('RACKBEAT_API_KEY', 'NOT SET')[:50]}...")
print(f"RACKBEAT_ENDPOINT: {os.getenv('RACKBEAT_ENDPOINT', 'NOT SET')}")
print(f"SHOPIFY_DOMAIN: {os.getenv('SHOPIFY_DOMAIN', 'NOT SET')}")
print(f"SHOPIFY_TOKEN: {os.getenv('SHOPIFY_TOKEN', 'NOT SET')[:20]}...")
print(f"SHOPIFY_VERSION: {os.getenv('SHOPIFY_VERSION', 'NOT SET')}")

# Test if we can import the sync service
try:
    print("\n=== SYNC SERVICE IMPORT TEST ===")
    import sync_service
    print("✓ Sync service imports successfully")
    print(f"RACKBEAT_ENDPOINT from sync_service: {sync_service.RACKBEAT_ENDPOINT}")
    print(f"SHOPIFY_DOMAIN from sync_service: {sync_service.SHOPIFY_DOMAIN}")
except Exception as e:
    print(f"✗ Error importing sync service: {e}") 