#!/usr/bin/env python3
"""
Test direct vehicle-id based TecDoc lookup for Nissan X-Trail 2006
Using existing TecDoc integration to find vehicle-id and get compatible articles
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from rapidapi_tecdoc import (
    get_manufacturers, get_models_for_manufacturer, find_model_id,
    get_articles_for_vehicle, get_article_details
)

def test_nissan_xtrail_direct():
    """Test direct vehicle-id lookup for Nissan X-Trail 2006"""
    
    print("🔍 TESTING DIRECT VEHICLE-ID LOOKUP FOR NISSAN X-TRAIL 2006")
    print("=" * 60)
    
    # Step 1: Get Nissan manufacturer ID
    print("📋 Step 1: Getting manufacturers...")
    manufacturers_data = get_manufacturers()
    
    if not manufacturers_data or 'manufacturers' not in manufacturers_data:
        print("❌ No manufacturers data found")
        return
    
    manufacturers = manufacturers_data['manufacturers']
    
    nissan_id = None
    for manufacturer in manufacturers:
        if manufacturer.get('brand', '').upper() == 'NISSAN':
            nissan_id = manufacturer.get('manufacturerId')
            print(f"✅ Found Nissan manufacturer ID: {nissan_id}")
            break
    
    if not nissan_id:
        print("❌ Nissan manufacturer not found")
        return
    
    # Step 2: Get Nissan models
    print(f"\n📋 Step 2: Getting Nissan models...")
    models = get_models_for_manufacturer(nissan_id)
    
    if not models:
        print("❌ No Nissan models found")
        return
    
    print(f"✅ Found {len(models)} Nissan models")
    
    # Step 3: Find vehicle-id for X-Trail 2006
    print(f"\n📋 Step 3: Finding vehicle-id for X-Trail 2006...")
    vehicle_id = find_model_id("X-TRAIL", "2006", models)
    
    if not vehicle_id:
        print("❌ No vehicle-id found for X-Trail 2006")
        return
    
    print(f"✅ Found vehicle-id for X-Trail 2006: {vehicle_id}")
    
    # Step 4: Get articles for both product groups
    print(f"\n📋 Step 4: Getting articles for vehicle-id {vehicle_id}...")
    
    # Test both Drivaksler (100260) and Mellomaksler (100270)
    product_groups = [
        (100260, "Drivaksler"),
        (100270, "Mellomaksler")
    ]
    
    all_articles = []
    
    for product_group_id, group_name in product_groups:
        print(f"\n🔍 Testing {group_name} (product group {product_group_id})...")
        
        articles = get_articles_for_vehicle(vehicle_id, product_group_id, nissan_id)
        
        if articles:
            print(f"✅ Found {len(articles)} {group_name} articles")
            all_articles.extend(articles)
            
            # Check first few articles for OEM numbers
            print(f"🔍 Checking first 3 articles for OEM numbers...")
            for i, article in enumerate(articles[:3]):
                article_id = article.get('articleId')
                article_name = article.get('articleProductName', 'N/A')
                
                print(f"   Article {i+1}: {article_name} (ID: {article_id})")
                
                # Get article details to check OEMs
                details = get_article_details(article_id)
                if details:
                    oem_numbers = details.get('articleOemNo', [])
                    if oem_numbers:
                        print(f"      OEM numbers:")
                        for oem in oem_numbers:
                            oem_no = oem.get('oemDisplayNo', 'N/A')
                            oem_brand = oem.get('oemBrand', 'N/A')
                            print(f"        - {oem_no} ({oem_brand})")
                            
                            # Check for our known Nissan OEMs
                            if oem_no in ['370008H310', '370008H510', '370008H800']:
                                print(f"        🎯 FOUND MATCHING NISSAN OEM: {oem_no}!")
                    else:
                        print(f"      No OEM numbers found")
                else:
                    print(f"      Failed to get article details")
        else:
            print(f"❌ No {group_name} articles found")
    
    # Summary
    print(f"\n📊 SUMMARY:")
    print(f"Vehicle ID: {vehicle_id}")
    print(f"Total articles found: {len(all_articles)}")
    
    if all_articles:
        print(f"✅ SUCCESS! Direct vehicle-id lookup works for Nissan X-Trail 2006")
        print(f"💡 This approach can be used to get all compatible parts directly from TecDoc")
        
        # Check if we found any articles with our target OEMs
        target_oems = ['370008H310', '370008H510', '370008H800']
        found_target_oems = False
        
        print(f"\n🎯 Checking all articles for target OEMs: {target_oems}")
        for article in all_articles[:10]:  # Check first 10 articles
            article_id = article.get('articleId')
            details = get_article_details(article_id)
            if details:
                oem_numbers = details.get('articleOemNo', [])
                for oem in oem_numbers:
                    oem_no = oem.get('oemDisplayNo', '')
                    if oem_no in target_oems:
                        print(f"🎯 FOUND TARGET OEM {oem_no} in article {article_id}!")
                        found_target_oems = True
        
        if found_target_oems:
            print(f"✅ SUCCESS! Found articles with target Nissan OEMs")
        else:
            print(f"⚠️ No articles found with target OEMs in first 10 articles")
            print(f"💡 May need to check more articles or different product groups")
    else:
        print(f"❌ FAILED! No articles found for Nissan X-Trail 2006")

if __name__ == "__main__":
    test_nissan_xtrail_direct()
