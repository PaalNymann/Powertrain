#!/usr/bin/env python3
"""
Final OEM-based TecDoc solution for Nissan X-Trail compatibility
Uses direct OEM search to find all compatible propshaft/drive shaft articles
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import requests
from typing import List, Dict, Set

# RapidAPI TecDoc Configuration
RAPIDAPI_KEY = "48a6ede874mshe38f052cb6a6109p12916fjsn0d0c0912c5ed"
BASE_URL = "https://tecdoc-catalog.p.rapidapi.com"
HEADERS = {
    'x-rapidapi-host': 'tecdoc-catalog.p.rapidapi.com',
    'x-rapidapi-key': RAPIDAPI_KEY
}

LANG_ID = 4  # English

def get_articles_by_oem(oem_number: str) -> List[Dict]:
    """Get all articles for a specific OEM number"""
    url = f"{BASE_URL}/articles-oem/search/lang-id/{LANG_ID}/article-oem-search-no/{oem_number}"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        if response.status_code == 200:
            articles = response.json()
            if isinstance(articles, list):
                return articles
            else:
                print(f"⚠️ Unexpected response format for OEM {oem_number}: {type(articles)}")
                return []
        else:
            print(f"❌ Failed to get articles for OEM {oem_number}: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ Exception getting articles for OEM {oem_number}: {e}")
        return []

def get_article_details(article_id: int) -> Dict:
    """Get detailed information for a specific article"""
    url = f"{BASE_URL}/articles/details/{article_id}/lang-id/{LANG_ID}/country-filter-id/62"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Failed to get details for article {article_id}: {response.status_code}")
            return {}
    except Exception as e:
        print(f"❌ Exception getting details for article {article_id}: {e}")
        return {}

def find_compatible_articles_for_nissan_xtrail() -> Dict:
    """Find all compatible articles for Nissan X-Trail using known OEMs"""
    
    print("🔍 FINDING COMPATIBLE ARTICLES FOR NISSAN X-TRAIL")
    print("=" * 60)
    
    # Known Nissan X-Trail OEMs for propshafts/drive shafts
    target_oems = [
        "370008H310",
        "370008H510", 
        "370008H800"
    ]
    
    all_articles = {}
    all_oem_numbers = set()
    
    print(f"🔍 Searching for articles using {len(target_oems)} known OEMs...")
    
    for oem in target_oems:
        print(f"\n📋 Processing OEM: {oem}")
        
        articles = get_articles_by_oem(oem)
        
        if articles:
            print(f"✅ Found {len(articles)} articles for OEM {oem}")
            
            for article in articles:
                article_id = article.get('articleId')
                article_name = article.get('articleProductName', 'N/A')
                supplier = article.get('supplierName', 'N/A')
                
                if article_id and article_id not in all_articles:
                    # Get detailed information
                    details = get_article_details(article_id)
                    
                    if details:
                        # Extract all OEM numbers for this article
                        oem_numbers = details.get('articleOemNo', [])
                        article_oems = []
                        
                        for oem_data in oem_numbers:
                            oem_no = oem_data.get('oemDisplayNo', '')
                            oem_brand = oem_data.get('oemBrand', '')
                            if oem_no:
                                article_oems.append(f"{oem_no} ({oem_brand})")
                                all_oem_numbers.add(oem_no)
                        
                        # Store article with all its information
                        all_articles[article_id] = {
                            'id': article_id,
                            'name': article_name,
                            'supplier': supplier,
                            'oem_numbers': article_oems,
                            'found_via_oem': oem,
                            'article_data': article,
                            'details_data': details
                        }
                        
                        print(f"   📦 {article_name} (ID: {article_id}, Supplier: {supplier})")
                        print(f"      OEMs: {', '.join(article_oems[:3])}{'...' if len(article_oems) > 3 else ''}")
                    else:
                        print(f"   ⚠️ Could not get details for article {article_id}")
        else:
            print(f"❌ No articles found for OEM {oem}")
    
    print(f"\n📊 SUMMARY:")
    print(f"Total unique articles found: {len(all_articles)}")
    print(f"Total unique OEM numbers discovered: {len(all_oem_numbers)}")
    
    return {
        'articles': all_articles,
        'all_oems': sorted(list(all_oem_numbers)),
        'target_oems': target_oems
    }

def analyze_compatibility_coverage(results: Dict):
    """Analyze how well our OEM-based approach covers compatibility"""
    
    print(f"\n🔍 ANALYZING COMPATIBILITY COVERAGE")
    print("=" * 50)
    
    articles = results['articles']
    all_oems = results['all_oems']
    target_oems = results['target_oems']
    
    if not articles:
        print("❌ No articles found to analyze")
        return
    
    print(f"📋 Article Analysis:")
    
    # Group articles by type/name
    article_types = {}
    for article_id, article_data in articles.items():
        name = article_data['name']
        if name not in article_types:
            article_types[name] = []
        article_types[name].append(article_data)
    
    for article_type, type_articles in article_types.items():
        print(f"\n🔧 {article_type}:")
        print(f"   Count: {len(type_articles)}")
        print(f"   Suppliers: {', '.join(set(a['supplier'] for a in type_articles))}")
        
        # Show unique OEMs for this article type
        type_oems = set()
        for article in type_articles:
            for oem_str in article['oem_numbers']:
                oem_no = oem_str.split(' (')[0]  # Extract just the OEM number
                type_oems.add(oem_no)
        
        print(f"   Unique OEMs: {len(type_oems)}")
        if len(type_oems) <= 10:
            print(f"   OEMs: {', '.join(sorted(type_oems))}")
        else:
            print(f"   Sample OEMs: {', '.join(sorted(list(type_oems))[:10])}...")
    
    print(f"\n📋 OEM Coverage Analysis:")
    print(f"Started with {len(target_oems)} target OEMs")
    print(f"Discovered {len(all_oems)} total OEMs from articles")
    
    # Find additional OEMs we could use for broader compatibility
    additional_oems = [oem for oem in all_oems if oem not in target_oems]
    if additional_oems:
        print(f"🎯 Found {len(additional_oems)} additional OEMs for broader compatibility:")
        for oem in additional_oems[:20]:  # Show first 20
            print(f"   - {oem}")
        if len(additional_oems) > 20:
            print(f"   ... and {len(additional_oems) - 20} more")

def test_backend_integration(results: Dict):
    """Test how this would integrate with our backend search"""
    
    print(f"\n🔍 BACKEND INTEGRATION TEST")
    print("=" * 40)
    
    articles = results['articles']
    all_oems = results['all_oems']
    
    if not articles:
        print("❌ No articles to test integration with")
        return
    
    print(f"📋 Integration Strategy:")
    print(f"1. For Nissan X-Trail (ZT41818), use OEM-based TecDoc search")
    print(f"2. Search TecDoc for each OEM: {', '.join(results['target_oems'])}")
    print(f"3. Collect all unique articles and their OEM numbers")
    print(f"4. Match collected OEMs against Shopify products (Original_nummer field)")
    print(f"5. Return matching products to user")
    
    print(f"\n📋 Expected Results:")
    print(f"- TecDoc articles found: {len(articles)}")
    print(f"- Unique OEMs to match: {len(all_oems)}")
    print(f"- Article types: {len(set(a['name'] for a in articles.values()))}")
    
    # Show what OEMs we would search for in Shopify
    print(f"\n🔍 OEMs to search in Shopify database:")
    for i, oem in enumerate(all_oems[:15]):  # Show first 15
        print(f"   {i+1:2d}. {oem}")
    if len(all_oems) > 15:
        print(f"   ... and {len(all_oems) - 15} more OEMs")
    
    print(f"\n💡 This approach should find MA18002 if:")
    print(f"1. MA18002 has any of these OEMs in its Original_nummer field")
    print(f"2. MA18002 is properly synced to Shopify with correct metafields")
    print(f"3. The OEM matching logic handles format variations (spaces, case, etc.)")

if __name__ == "__main__":
    # Find all compatible articles using OEM-based search
    results = find_compatible_articles_for_nissan_xtrail()
    
    # Analyze the coverage and compatibility
    analyze_compatibility_coverage(results)
    
    # Test backend integration approach
    test_backend_integration(results)
    
    print(f"\n🎯 CONCLUSION:")
    if results['articles']:
        print(f"✅ OEM-based TecDoc search successfully finds compatible propshaft articles")
        print(f"✅ This approach should work for all vehicles with known OEMs")
        print(f"💡 Next step: Implement this in the backend for ZT41818 and similar cases")
    else:
        print(f"❌ OEM-based search failed - need to investigate further")
