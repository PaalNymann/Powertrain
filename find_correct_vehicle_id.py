#!/usr/bin/env python3
"""
Find the correct vehicle ID in RapidAPI TecDoc that matches our Rackbeat OEM numbers
"""

import requests
import json
import time

# RapidAPI TecDoc Configuration
RAPIDAPI_KEY = "48a6ede874mshe38f052cb6a6109p12916fjsn0d0c0912c5ed"
BASE_URL = "https://tecdoc-catalog.p.rapidapi.com"
HEADERS = {
    'x-rapidapi-host': 'tecdoc-catalog.p.rapidapi.com',
    'x-rapidapi-key': RAPIDAPI_KEY
}

# Known Rackbeat OEM numbers for 2006 Volvo V70 left axle
KNOWN_RACKBEAT_OEMS = [
    '30735120', '30735349', '30783083', '30783085', '36000520', '36000526',
    '8252034', '8252035', '8252043', '8601855', '8601859', '8602577', 
    '8602591', '8602842', '86028420', '8603794', '8603795', '8689213', 
    '8689227', '8689872', '9181255', '9181261'
]

def get_articles_for_vehicle_id(vehicle_id, manufacturer_id=120, product_group_id=100260):
    """Get articles for a specific vehicle ID"""
    url = (f"{BASE_URL}/articles/list/"
           f"vehicle-id/{vehicle_id}/"
           f"product-group-id/{product_group_id}/"
           f"manufacturer-id/{manufacturer_id}/"
           f"lang-id/4/country-filter-id/62/type-id/1")
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except Exception as e:
        print(f"Error getting articles for vehicle {vehicle_id}: {e}")
        return None

def extract_oem_numbers_from_articles(articles_data):
    """Extract OEM numbers from articles response"""
    oem_numbers = []
    
    if not articles_data or 'articles' not in articles_data:
        return oem_numbers
    
    for article in articles_data['articles']:
        # Get OEM numbers from the article
        if 'oemNo' in article and isinstance(article['oemNo'], list):
            for oem_entry in article['oemNo']:
                if isinstance(oem_entry, dict):
                    oem_display_no = oem_entry.get('oemDisplayNo', '').strip()
                    if oem_display_no:
                        # Clean up OEM number (remove spaces, standardize format)
                        oem_clean = oem_display_no.replace(' ', '').replace('-', '')
                        oem_numbers.append(oem_clean)
    
    return list(set(oem_numbers))

def find_matching_vehicle_ids(start_id=19000, end_id=20500, manufacturer_id=120):
    """
    Search through vehicle IDs to find ones that return our known Rackbeat OEM numbers
    """
    print(f"🔍 Searching vehicle IDs {start_id} to {end_id} for Volvo (manufacturer {manufacturer_id})")
    print(f"Looking for these Rackbeat OEMs: {KNOWN_RACKBEAT_OEMS[:5]}... (and {len(KNOWN_RACKBEAT_OEMS)-5} more)")
    
    matches = []
    
    for vehicle_id in range(start_id, end_id + 1):
        if vehicle_id % 50 == 0:
            print(f"  Testing vehicle ID {vehicle_id}...")
        
        # Get articles for this vehicle ID
        articles_data = get_articles_for_vehicle_id(vehicle_id, manufacturer_id)
        
        if articles_data and articles_data.get('countArticles', 0) > 0:
            # Extract OEM numbers
            oem_numbers = extract_oem_numbers_from_articles(articles_data)
            
            # Check for matches with known Rackbeat OEMs
            matching_oems = []
            for rackbeat_oem in KNOWN_RACKBEAT_OEMS:
                if rackbeat_oem in oem_numbers:
                    matching_oems.append(rackbeat_oem)
            
            if matching_oems:
                article_count = articles_data.get('countArticles', 0)
                print(f"✅ MATCH! Vehicle ID {vehicle_id}: {len(matching_oems)} matching OEMs, {article_count} total articles")
                print(f"   Matching OEMs: {matching_oems}")
                
                matches.append({
                    'vehicle_id': vehicle_id,
                    'matching_oems': matching_oems,
                    'total_articles': article_count,
                    'all_oems': oem_numbers[:10]  # First 10 for reference
                })
        
        # Rate limiting
        time.sleep(0.1)
    
    return matches

def main():
    """Find the correct vehicle ID for 2006 Volvo V70"""
    print("🚗 Finding correct vehicle ID for 2006 Volvo V70 in RapidAPI TecDoc")
    print("=" * 70)
    
    # Search around the current vehicle ID (19942) that we know works but returns wrong OEMs
    matches = find_matching_vehicle_ids(19800, 20200, manufacturer_id=120)
    
    if matches:
        print(f"\n🎉 Found {len(matches)} vehicle IDs with matching OEMs:")
        for match in matches:
            print(f"  Vehicle ID {match['vehicle_id']}: {len(match['matching_oems'])} matches")
            print(f"    Matching: {match['matching_oems']}")
            print(f"    Total articles: {match['total_articles']}")
            print()
    else:
        print("\n❌ No vehicle IDs found with matching Rackbeat OEMs in the tested range")
        print("   Try expanding the search range or checking different manufacturer IDs")

if __name__ == "__main__":
    main()
