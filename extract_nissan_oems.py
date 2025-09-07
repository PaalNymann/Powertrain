#!/usr/bin/env python3
"""
Extract OEMs from Successful Nissan Search
Analyze the 4 results from /articles-oem/search for Nissan
"""

import requests
import json

def extract_nissan_oems():
    """Extract OEMs from the successful Nissan search endpoint"""
    
    rapidapi_key = "48a6ede874mshe38f052cb6a6109p12916fjsn0d0c0912c5ed"
    base_url = "https://tecdoc-catalog.p.rapidapi.com"
    headers = {
        'x-rapidapi-host': 'tecdoc-catalog.p.rapidapi.com',
        'x-rapidapi-key': rapidapi_key
    }
    
    print("🔍 EXTRACTING OEMS FROM SUCCESSFUL NISSAN SEARCH")
    print("=" * 60)
    
    try:
        url = f"{base_url}/articles-oem/search/lang-id/4/article-oem-search-no/Nissan"
        print(f"URL: {url}")
        
        response = requests.get(url, headers=headers, timeout=15)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Results: {len(data)} articles found")
            
            print(f"\n📋 FULL RESPONSE:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            
            # Extract OEMs from each article
            all_oems = []
            
            print(f"\n🔍 EXTRACTING OEMS FROM EACH ARTICLE:")
            for i, article in enumerate(data):
                print(f"\n--- Article {i+1} ---")
                print(f"Article ID: {article.get('articleId')}")
                print(f"Article No: {article.get('articleNo')}")
                print(f"Product Name: {article.get('articleProductName')}")
                
                # Look for OEM numbers in different possible fields
                oem_fields = ['oemNumbers', 'oems', 'oemNumber', 'oem', 'partNumbers', 'partNumber']
                
                for field in oem_fields:
                    if field in article:
                        oem_data = article[field]
                        print(f"Found {field}: {oem_data}")
                        
                        if isinstance(oem_data, list):
                            for oem_item in oem_data:
                                if isinstance(oem_item, dict):
                                    oem_number = oem_item.get('oemNumber') or oem_item.get('number') or oem_item.get('value')
                                    if oem_number:
                                        all_oems.append(oem_number)
                                        print(f"  → OEM: {oem_number}")
                                elif isinstance(oem_item, str):
                                    all_oems.append(oem_item)
                                    print(f"  → OEM: {oem_item}")
                        elif isinstance(oem_data, str):
                            all_oems.append(oem_data)
                            print(f"  → OEM: {oem_data}")
                
                # Also check if we need to make additional API calls to get OEM details
                article_id = article.get('articleId')
                if article_id:
                    print(f"Article ID {article_id} - checking for additional OEM endpoint...")
                    
                    # Try to get OEM details for this specific article
                    try:
                        oem_detail_url = f"{base_url}/articles/{article_id}/oems"
                        oem_response = requests.get(oem_detail_url, headers=headers, timeout=10)
                        if oem_response.status_code == 200:
                            oem_details = oem_response.json()
                            print(f"  Additional OEM details: {oem_details}")
                            
                            if isinstance(oem_details, list):
                                for oem_detail in oem_details:
                                    if isinstance(oem_detail, dict):
                                        oem_num = oem_detail.get('oemNumber') or oem_detail.get('number')
                                        if oem_num and oem_num not in all_oems:
                                            all_oems.append(oem_num)
                                            print(f"    → Additional OEM: {oem_num}")
                        else:
                            print(f"  No additional OEM details (status: {oem_response.status_code})")
                    except Exception as e:
                        print(f"  Error getting additional OEMs: {e}")
            
            print(f"\n🎯 SUMMARY:")
            print(f"Total unique OEMs found: {len(set(all_oems))}")
            unique_oems = list(set(all_oems))
            
            if unique_oems:
                print(f"All OEMs: {unique_oems}")
                
                # Check for customer-verified OEMs
                customer_oems = ['370008H310', '370008H510', '370008H800', '37000-8H310', '37000-8H510', '37000-8H800']
                found_customer_oems = []
                
                for customer_oem in customer_oems:
                    for found_oem in unique_oems:
                        if (customer_oem.replace('-', '').replace(' ', '').upper() == 
                            found_oem.replace('-', '').replace(' ', '').upper()):
                            found_customer_oems.append((customer_oem, found_oem))
                
                if found_customer_oems:
                    print(f"🎉 CUSTOMER-VERIFIED OEMs FOUND: {found_customer_oems}")
                else:
                    print(f"⚠️ Customer-verified OEMs not found in this search")
                    print(f"Expected: {customer_oems}")
                
                return unique_oems
            else:
                print("❌ No OEMs extracted from articles")
                return []
                
        else:
            print(f"❌ Request failed: {response.status_code}")
            print(f"Response: {response.text}")
            return []
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return []

if __name__ == "__main__":
    extract_nissan_oems()
