#!/usr/bin/env python3
"""
Analyze Rackbeat product fields to understand the correct metafield mapping
"""

import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

RACKBEAT_API = os.getenv("RACKBEAT_ENDPOINT", "https://app.rackbeat.com/api/products")
RACKBEAT_KEY = os.getenv("RACKBEAT_API_KEY")

HEADERS = {
    "Authorization": f"Bearer {RACKBEAT_KEY}",
    "Content-Type": "application/json"
}

def analyze_rackbeat_fields():
    print("🔍 ANALYZING RACKBEAT PRODUCT FIELDS")
    print("=" * 40)
    
    # Get first page of products
    url = f"{RACKBEAT_API}?page=1&limit=10"
    response = requests.get(url, headers=HEADERS, timeout=30)
    
    if response.status_code not in [200, 206]:
        print(f"❌ Error: {response.status_code}")
        return
    
    data = response.json()
    products = data["products"]
    
    if not products:
        print("❌ No products found")
        return
    
    print(f"📊 Analyzing {len(products)} sample products...")
    
    # Analyze the first product in detail
    sample_product = products[0]
    print(f"\n📋 Sample product: {sample_product.get('name', 'N/A')}")
    print(f"SKU: {sample_product.get('number', 'N/A')}")
    
    print("\n🔍 ALL AVAILABLE FIELDS:")
    print("-" * 30)
    
    for key, value in sample_product.items():
        if isinstance(value, str) and len(value) > 100:
            value = value[:100] + "..."
        print(f"{key}: {value}")
    
    print("\n🎯 POTENTIAL OEM/COMPATIBILITY FIELDS:")
    print("-" * 40)
    
    # Look for fields that might contain OEM numbers
    oem_candidates = []
    for key, value in sample_product.items():
        key_lower = key.lower()
        if any(term in key_lower for term in ['oem', 'original', 'nummer', 'number', 'part', 'compat']):
            oem_candidates.append((key, value))
        elif isinstance(value, str) and any(term in value.lower() for term in ['oem', 'original', 'compatible']):
            oem_candidates.append((key, value))
    
    for key, value in oem_candidates:
        print(f"🔍 {key}: {value}")
    
    print("\n📝 DESCRIPTION FIELD ANALYSIS:")
    print("-" * 35)
    description = sample_product.get('description', '')
    if description:
        print(f"Description: {description[:200]}...")
        
        # Look for OEM patterns in description
        import re
        oem_patterns = [
            r'\b[A-Z]{2,4}\d{3,8}\b',  # Common OEM patterns like BMW123456
            r'\b\d{6,10}\b',           # 6-10 digit numbers
            r'\b[A-Z0-9]{6,12}\b',     # Alphanumeric codes
        ]
        
        for pattern in oem_patterns:
            matches = re.findall(pattern, description)
            if matches:
                print(f"Potential OEM numbers found: {matches[:5]}")  # Show first 5
    
    print("\n🏷️ CURRENT METAFIELD MAPPING:")
    print("-" * 35)
    
    current_mapping = {
        "original_nummer": sample_product.get("description", ""),
        "spicer_varenummer": sample_product.get("spicer_number", ""),
        "industries_varenummer": sample_product.get("industries_number", ""),
        "inntektskonto": sample_product.get("inntektskonto", ""),
        "tirsan_varenummer": sample_product.get("tirsan_number", ""),
        "odm_varenummer": sample_product.get("odm_number", ""),
        "ims_varenummer": sample_product.get("ims_number", ""),
        "welte_varenummer": sample_product.get("welte_number", ""),
        "bakkeren_varenummer": sample_product.get("bakkeren_number", ""),
    }
    
    for key, value in current_mapping.items():
        if value:
            print(f"✅ {key}: {value[:50]}...")
        else:
            print(f"❌ {key}: (empty)")
    
    # Check if there are any 'fields' or 'custom_fields' objects
    print("\n🔍 CHECKING FOR NESTED FIELD STRUCTURES:")
    print("-" * 40)
    
    for key, value in sample_product.items():
        if isinstance(value, dict):
            print(f"📁 {key}: {list(value.keys())}")
        elif isinstance(value, list) and value and isinstance(value[0], dict):
            print(f"📁 {key}: {list(value[0].keys())}")

if __name__ == "__main__":
    analyze_rackbeat_fields() 