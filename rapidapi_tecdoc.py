#!/usr/bin/env python3
"""
RapidAPI TecDoc Integration Module - Two-Step Workflow
1. VIN Decoder API -> vehicleId
2. TecDoc Catalog API -> Parts & OEMs
"""

import requests
import time
from typing import List, Dict, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- API Configurations ---
CATALOG_RAPIDAPI_KEY = "48a6ede874mshe38f052cb6a6109p12916fjsn0d0c0912c5ed"
CATALOG_BASE_URL = "https://tecdoc-catalog.p.rapidapi.com"
CATALOG_HEADERS = {
    'x-rapidapi-host': 'tecdoc-catalog.p.rapidapi.com',
    'x-rapidapi-key': CATALOG_RAPIDAPI_KEY
}

VIN_DECODER_API_KEY = "730aa880femshf8a70dec6a53325p1f50ccjsn3bcc61a5cbb3"
VIN_DECODER_BASE_URL = "https://vin-decoder-support-tecdoc-catalog.p.rapidapi.com/"
VIN_DECODER_HEADERS = {
    'x-rapidapi-host': 'vin-decoder-support-tecdoc-catalog.p.rapidapi.com',
    'x-rapidapi-key': VIN_DECODER_API_KEY
}

import os
from database import get_cached_oems_for_article, upsert_article_oems
# --- TecDoc Constants ---
LANG_ID = 4
COUNTRY_ID = 62  # Stick to stable country filter used previously
TYPE_ID = 1      # Passenger cars only
# Performance knobs (env overridable)
MAX_ARTICLES_PER_GROUP = int(os.getenv('MAX_ARTICLES_PER_GROUP', '5'))  # details calls per group
PER_PAGE = MAX_ARTICLES_PER_GROUP
OEM_EARLY_EXIT_LIMIT = int(os.getenv('OEM_EARLY_EXIT_LIMIT', '50'))
# Per user's confirmation: use these two product groups
PRODUCT_GROUPS = [(100062, "Drivaksler"), (100703, "Mellomaksler")]
# Only accept these article names (automotive shafts). Prevents air filters/wipers etc.
ALLOWED_ARTICLE_NAMES = {"Drive Shaft", "Propshaft, axle drive"}

# --- Core API Functions ---
def get_vehicle_id_from_vin(vin: str) -> Optional[int]:
    """Gets TecDoc vehicleId (k-type) from a VIN."""
    print(f"📡 Decoding VIN to get vehicleId for: {vin}")
    try:
        response = requests.get(VIN_DECODER_BASE_URL, headers=VIN_DECODER_HEADERS, params={'vin': vin, 'country': 'DE'}, timeout=15)
        if response.status_code == 200:
            vehicle_id = response.json().get('data', {}).get('AWN_k_type')
            if vehicle_id and str(vehicle_id) != "INCONNU":
                print(f"✅ Successfully decoded VIN to vehicleId: {vehicle_id}")
                return int(vehicle_id)
        print(f"❌ VIN decoder failed. Status: {response.status_code}, Response: {response.text[:100]}")
        return None
    except requests.RequestException as e:
        print(f"❌ Exception during VIN decoder request: {e}")
        return None

def get_oem_numbers_from_rapidapi_tecdoc(vin: str) -> List[str]:
    """Main workflow to get OEM numbers for a given VIN."""
    vehicle_id = get_vehicle_id_from_vin(vin)
    if not vehicle_id:
        return []

    all_oems = set()
    for group_id, group_name in PRODUCT_GROUPS:
        print(f"\n🔍 Searching for '{group_name}' (ID: {group_id}) for vehicleId: {vehicle_id}")
        try:
            # Use Ron's correct endpoint: POST /articles/list-articles (x-www-form-urlencoded)
            articles_url = f"{CATALOG_BASE_URL}/articles/list-articles"
            payload = (
                f"langId={LANG_ID}&countryId={COUNTRY_ID}&typeId={TYPE_ID}"
                f"&vehicleId={vehicle_id}&productGroupId={group_id}&page=1&perPage={PER_PAGE}"
            )
            print(f"   -> list-articles payload: {payload}")
            headers = {**CATALOG_HEADERS, 'content-type': 'application/x-www-form-urlencoded'}
            response = requests.post(articles_url, headers=headers, data=payload, timeout=30)
            print(f"   -> Articles API call (POST list-articles) returned status: {response.status_code}")
            if response.status_code != 200:
                print(f"   -> Error response: {response.text[:200]}")
                continue
            
            data = response.json()
            articles = []
            if isinstance(data, dict):
                raw_articles = data.get('articles')
                if raw_articles is None and isinstance(data.get('data'), dict):
                    raw_articles = data['data'].get('articles')
                if isinstance(raw_articles, list):
                    # Filter strictly by allowed article names
                    filtered = []
                    for a in raw_articles:
                        name = a.get('genericArticleName') or a.get('articleProductName') or ''
                        if name in ALLOWED_ARTICLE_NAMES:
                            filtered.append(a)
                    articles = filtered
                else:
                    print(f"   -> Unexpected response format; keys: {list(data.keys())}")
            else:
                print(f"   -> Unexpected non-dict JSON response type: {type(data)}")

            print(f"   📦 Found {len(articles)} articles for '{group_name}'.")
            # Cap processing to first N to avoid excessive network time
            for article in articles[:MAX_ARTICLES_PER_GROUP]:
                # 1) Try OEMs directly from list-articles if present
                oem_list = article.get('oeNumbers')
                if isinstance(oem_list, list) and oem_list:
                    for oem in oem_list:
                        if isinstance(oem, dict):
                            val = oem.get('oeNumber') or oem.get('articleOemNo')
                        else:
                            val = str(oem)
                        if val:
                            all_oems.add(val.strip())
                    # Early exit if we already have plenty of OEMs
                    if len(all_oems) >= OEM_EARLY_EXIT_LIMIT:
                        break
                    continue

                # 1b) Cache-first: see if we already have OEMs for this articleId
                article_id = article.get('articleId')
                if article_id:
                    cached = get_cached_oems_for_article(str(article_id))
                    if cached:
                        for val in cached:
                            all_oems.add(val)
                        if len(all_oems) >= OEM_EARLY_EXIT_LIMIT:
                            break
                        continue

                # 2) Otherwise call POST /articles/details to fetch OEMs for this articleId
                if not article_id:
                    continue
                try:
                    details_url = f"{CATALOG_BASE_URL}/articles/details"
                    details_payload = f"langId={LANG_ID}&countryId={COUNTRY_ID}&articleId={article_id}"
                    details_headers = {**CATALOG_HEADERS, 'content-type': 'application/x-www-form-urlencoded'}
                    dres = requests.post(details_url, headers=details_headers, data=details_payload, timeout=8)
                    if dres.status_code != 200:
                        print(f"   -> details status {dres.status_code} for articleId {article_id}")
                        continue
                    dj = dres.json()
                    # Expected: {'articleId': '...', 'article': {...}, 'articleOemNo': [ {oemBrand, oemDisplayNo}, ... ]}
                    oem_items = []
                    if isinstance(dj, dict):
                        # primary key observed in tests
                        if isinstance(dj.get('articleOemNo'), list):
                            oem_items.extend(dj['articleOemNo'])
                        # also check alternative keys
                        for alt in ('oemNumbers', 'oeNumbers'):
                            val = dj.get(alt)
                            if isinstance(val, list):
                                oem_items.extend(val)
                    collected = []
                    for it in oem_items:
                        if isinstance(it, dict):
                            val = it.get('oemDisplayNo') or it.get('oemNumber') or it.get('oeNumber') or it.get('articleOemNo')
                        else:
                            val = str(it)
                        if val:
                            sval = val.strip()
                            all_oems.add(sval)
                            collected.append(sval)
                    # Upsert into cache for future requests
                    try:
                        upsert_article_oems(
                            article_id=str(article_id),
                            product_group_id=group_id,
                            supplier_id=article.get('supplierId') or 0,
                            supplier_name=article.get('supplierName') or '',
                            article_product_name=article.get('articleProductName') or '',
                            oem_numbers=collected,
                        )
                    except Exception as ce:
                        print(f"   -> cache upsert error for {article_id}: {ce}")
                    # Early exit if we collected enough OEMs
                    if len(all_oems) >= OEM_EARLY_EXIT_LIMIT:
                        break
                except requests.RequestException as ex:
                    print(f"   -> details exception for articleId {article_id}: {ex}")

        except requests.RequestException as e:
            print(f"   ❌ Exception getting articles: {e}")
            continue
    
    return list(all_oems)

# --- Test Function ---
def test_workflow():
    """Tests the full, live VIN-to-OEM workflow."""
    print("\n🧪🧪🧪--- Running Test: Full VIN-to-OEM Workflow ---🧪🧪🧪")
    test_vin = "WBA1A110007H68120"  # 2011 BMW 1 Series (F20)
    oem_numbers = get_oem_numbers_from_rapidapi_tecdoc(test_vin)
    
    if oem_numbers:
        print(f"\n✅✅✅ Test successful! Found {len(oem_numbers)} OEM numbers.")
    else:
        print("\n❌❌❌ Test failed: No OEM numbers were found.")

if __name__ == "__main__":
    test_workflow()
