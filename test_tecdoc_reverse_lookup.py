#!/usr/bin/env python3
"""
TecDoc Reverse Lookup Test
Search for known Nissan OEMs in TecDoc to find correct vehicle/product group logic
"""

import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
RAPIDAPI_HOST = "tecdoc-api.p.rapidapi.com"

HEADERS = {
    "X-RapidAPI-Key": RAPIDAPI_KEY,
    "X-RapidAPI-Host": RAPIDAPI_HOST
}

def search_oem_in_tecdoc(oem_number):
    """Search for specific OEM number in TecDoc to see what vehicles/products it returns"""
    print(f"\n🔍 REVERSE LOOKUP: {oem_number}")
    print("=" * 50)
    
    # Try TecDoc OEM search endpoint
    url = f"https://{RAPIDAPI_HOST}/articles-oem/search"
    params = {
        "oem": oem_number,
        "limit": 10
    }
    
    try:
        response = requests.get(url, headers=HEADERS, params=params, timeout=30)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            if 'articles' in data and data['articles']:
                articles = data['articles']
                print(f"✅ Found {len(articles)} articles for OEM {oem_number}")
                
                for i, article in enumerate(articles[:3]):  # Show first 3
                    print(f"\nArticle {i+1}:")
                    print(f"   ID: {article.get('articleId', 'N/A')}")
                    print(f"   Brand: {article.get('brandName', 'N/A')}")
                    print(f"   Description: {article.get('articleName', 'N/A')[:60]}")
                    
                    # Check if we can get vehicle info for this article
                    if article.get('articleId'):
                        get_vehicle_info_for_article(article['articleId'])
                        
            else:
                print(f"❌ No articles found for OEM {oem_number}")
                
        elif response.status_code == 404:
            print(f"❌ Endpoint not found - trying alternative search...")
            # Try alternative search methods
            search_oem_alternative(oem_number)
            
        else:
            print(f"❌ API Error: {response.status_code}")
            print(f"Response: {response.text[:200]}")
            
    except Exception as e:
        print(f"❌ Error searching OEM {oem_number}: {e}")

def get_vehicle_info_for_article(article_id):
    """Get vehicle compatibility info for specific article"""
    print(f"   🚗 Getting vehicles for article {article_id}...")
    
    url = f"https://{RAPIDAPI_HOST}/articles/details/{article_id}"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            # Look for vehicle compatibility info
            if 'vehicles' in data:
                vehicles = data['vehicles'][:3]  # First 3 vehicles
                for vehicle in vehicles:
                    brand = vehicle.get('brandName', 'N/A')
                    model = vehicle.get('modelName', 'N/A')
                    year_from = vehicle.get('yearFrom', 'N/A')
                    year_to = vehicle.get('yearTo', 'N/A')
                    print(f"      → {brand} {model} ({year_from}-{year_to})")
                    
                    # Check if this matches our target (Nissan X-Trail 2006)
                    if 'NISSAN' in brand.upper() and 'X-TRAIL' in model.upper():
                        print(f"      ✅ MATCH: Found Nissan X-Trail!")
                        
            else:
                print(f"      ❌ No vehicle info available")
                
    except Exception as e:
        print(f"      ❌ Error getting vehicle info: {e}")

def search_oem_alternative(oem_number):
    """Try alternative TecDoc search methods"""
    print(f"   🔄 Trying alternative search for {oem_number}...")
    
    # Try direct article search
    url = f"https://{RAPIDAPI_HOST}/articles/search"
    params = {
        "query": oem_number,
        "limit": 5
    }
    
    try:
        response = requests.get(url, headers=HEADERS, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Alternative search successful")
            
            if 'articles' in data and data['articles']:
                print(f"   Found {len(data['articles'])} articles via alternative search")
            else:
                print(f"   No articles found via alternative search")
        else:
            print(f"   ❌ Alternative search failed: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Alternative search error: {e}")

def main():
    """Test reverse lookup with known MA18002 Nissan OEMs"""
    
    print("🎯 TECDOC REVERSE LOOKUP TEST")
    print("Testing MA18002 Nissan OEMs to find correct TecDoc logic")
    print("=" * 60)
    
    # Known Nissan OEMs for MA18002 (customer-verified for ZT41818)
    nissan_oems = [
        "37000-8H310",
        "37000-8H510", 
        "37000-8H800",
        "370008H310",
        "370008H510",
        "370008H800"
    ]
    
    print(f"Testing {len(nissan_oems)} known Nissan OEMs...")
    
    for oem in nissan_oems:
        search_oem_in_tecdoc(oem)
    
    print(f"\n💡 EXPECTED RESULTS:")
    print(f"   - Should find articles that are compatible with Nissan X-Trail 2006")
    print(f"   - Should reveal correct product groups and vehicle IDs")
    print(f"   - Should show why forward lookup (ZT41818 → OEMs) fails")
    print(f"   - Should guide us to fix the TecDoc API integration")

if __name__ == "__main__":
    main()
