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
import os

CATALOG_RAPIDAPI_KEY = os.getenv("CATALOG_RAPIDAPI_KEY")
# Make base URL and host configurable via env (endpoint-only change)
CATALOG_BASE_URL = os.getenv("TECDOC_CATALOG_BASE_URL", "https://tecdoc-catalog.p.rapidapi.com")
CATALOG_HOST = os.getenv("TECDOC_CATALOG_HOST", "tecdoc-catalog.p.rapidapi.com")
CATALOG_HEADERS = {
    'Content-Type': 'application/x-www-form-urlencoded',
    'x-rapidapi-host': CATALOG_HOST,
    'x-rapidapi-key': CATALOG_RAPIDAPI_KEY
}
# Allow overriding the list-articles path via env (default kept the same)
LIST_ARTICLES_PATH = os.getenv("TECDOC_LIST_ARTICLES_PATH", "/articles/list-articles")

VIN_DECODER_API_KEY = (
    os.getenv("VIN_DECODER_API_KEY")
    or os.getenv("RAPIDAPI_VIN_DECODER_KEY")
    or CATALOG_RAPIDAPI_KEY  # fallback to the same RapidAPI key if separate VIN key not provided
    or ""
)
VIN_DECODER_BASE_URL = "https://vin-decoder-support-tecdoc-catalog.p.rapidapi.com/"
VIN_DECODER_HEADERS = {
    'x-rapidapi-host': 'vin-decoder-support-tecdoc-catalog.p.rapidapi.com',
    'x-rapidapi-key': VIN_DECODER_API_KEY
}

# Simplified database imports for Railway compatibility
try:
    from database import get_vin_oem_cache, upsert_vin_oem_cache
except ImportError:
    # Fallback functions if database functions don't exist
    def get_vin_oem_cache(vin):
        return None
    def upsert_vin_oem_cache(vin, oem_numbers):
        pass

# Additional fallback functions for missing database functions
def get_cached_oems_for_article(article_id):
    return None

def upsert_article_oems(article_id, oem_numbers):
    pass

def get_vehicle_group_article_ids(vehicle_id, group_id):
    return []

def upsert_vehicle_group_article_ids(vehicle_id, group_id, article_ids):
    pass
# --- TecDoc Constants ---
LANG_ID = 4
COUNTRY_ID = 62  # Stick to stable country filter used previously
TYPE_ID = 1      # Passenger cars only
# Performance knobs (env overridable)
MAX_ARTICLES_PER_GROUP = int(os.getenv('MAX_ARTICLES_PER_GROUP', '5'))  # details calls per group
PER_PAGE = MAX_ARTICLES_PER_GROUP
OEM_EARLY_EXIT_LIMIT = int(os.getenv('OEM_EARLY_EXIT_LIMIT', '50'))
VIN_DB_CACHE_TTL_SECONDS = int(os.getenv('VIN_DB_CACHE_TTL_SECONDS', '86400'))  # 24h persistent cache
VEHICLE_GROUP_CACHE_TTL_SECONDS = int(os.getenv('VEHICLE_GROUP_CACHE_TTL_SECONDS', '604800'))  # 7 days
# TecDoc product group IDs for Drive Shaft and Propshaft
# Try multiple IDs since TecDoc structure varies by API provider
# We will search ALL of these and filter by keyword to find shaft articles
PRODUCT_GROUP_IDS_TO_TRY = [
    100050, 100060, 100080,  # Common drive shaft IDs
    100100, 100110, 100120,  # Alternative IDs
    100260, 100270, 100280,  # More alternatives
]
PRODUCT_GROUPS = [(gid, f"Category_{gid}") for gid in PRODUCT_GROUP_IDS_TO_TRY]
# Accept automotive shaft-related articles using flexible keyword matching (case-insensitive)
# This covers both drivaksler and mellomaksler common TecDoc names.
ALLOWED_ARTICLE_KEYWORDS = tuple(
    x.lower() for x in [
        "drive shaft",       # general drive shaft
        "propshaft",         # british/tecdoc term
        "propeller shaft",   # alternative naming
        "cardan",            # cardan shaft
        "intermediate shaft",# mellomaksel
        "axle drive",        # tecdoc term for propshaft/drive shaft
        "shaft"              # safe fallback within our targeted product groups
    ]
)

def _name_allowed(name: str) -> bool:
    n = str(name or '').strip().lower()
    return any(k in n for k in ALLOWED_ARTICLE_KEYWORDS)

# --- Category discovery (RapidAPI TecDoc) ---
def _discover_shaft_category_ids(vehicle_id: int) -> list[int]:
    """Query categories for a vehicle and return IDs whose names match our shaft keywords.
    Uses GET /categories/list with query params.
    """
    try:
        url = f"{CATALOG_BASE_URL}/categories/list"
        params = {"typeId": TYPE_ID, "vehicleId": vehicle_id, "langId": LANG_ID}
        r = requests.get(url, headers=CATALOG_HEADERS, params=params, timeout=10)
        if r.status_code != 200:
            print(f"   -> categories/list status {r.status_code}")
            return []
        data = r.json()
        cats = []
        # Expect either list at top-level or under 'data'
        raw = []
        if isinstance(data, list):
            raw = data
        elif isinstance(data, dict):
            maybe = data.get('data') or data.get('categories')
            if isinstance(maybe, list):
                raw = maybe
        for item in raw:
            if not isinstance(item, dict):
                continue
            cid = item.get('categoryId') or item.get('id') or item.get('assemblyGroupNodeId')
            name = item.get('categoryName') or item.get('name') or item.get('assemblyGroupName') or ''
            if cid and _name_allowed(name):
                try:
                    cats.append(int(cid))
                except Exception:
                    pass
        # Dedup
        cats = sorted(list({int(x) for x in cats}))
        print(f"   -> Discovered {len(cats)} shaft-related categoryIds: {cats[:8]}{'...' if len(cats)>8 else ''}")
        return cats
    except requests.RequestException as e:
        print(f"   -> categories/list exception: {e}")
        return []

# --- Core API Functions ---
def get_vehicle_id_from_vin(vin_or_vehicle_info) -> Optional[int]:
    """Get TecDoc vehicle ID from VIN using RapidAPI VIN Decoder with TecDoc support."""
    
    if not vin_or_vehicle_info:
        return None
    
    print(f"🔍 Finding vehicle ID for: {vin_or_vehicle_info}")
    
    try:
        # If we have a VIN string, use VIN Decoder API
        if isinstance(vin_or_vehicle_info, str) and len(vin_or_vehicle_info) == 17:
            vin = vin_or_vehicle_info
            print(f"📡 Using VIN Decoder API for VIN: {vin}")
            
            # Use correct VIN Decoder endpoint with TecDoc support
            VIN_DECODER_API_KEY = os.getenv("VIN_DECODER_API_KEY")
            if not VIN_DECODER_API_KEY:
                print("❌ VIN_DECODER_API_KEY not found in environment")
                return None
            
            url = f"https://vin-decoder-support-tecdoc-catalog.p.rapidapi.com/?vin={vin}&country=NO"
            
            headers = {
                'x-rapidapi-host': 'vin-decoder-support-tecdoc-catalog.p.rapidapi.com',
                'x-rapidapi-key': VIN_DECODER_API_KEY
            }
            
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('error') == False and 'data' in data:
                    vehicle_data = data['data']
                    
                    # Extract TecDoc Vehicle ID from k_type or id_version
                    vehicle_id = (vehicle_data.get('AWN_k_type') or 
                                 vehicle_data.get('AWN_id_version') or
                                 vehicle_data.get('AWN_tecdoc_modele_id'))
                    
                    if vehicle_id and vehicle_id != 'INCONNU':
                        make = vehicle_data.get('AWN_marque', 'Unknown')
                        model = vehicle_data.get('AWN_modele', 'Unknown')
                        year = vehicle_data.get('AWN_annee_de_debut_modele', 'Unknown')
                        
                        print(f"✅ Found TecDoc Vehicle ID {vehicle_id} for {make} {model} {year}")
                        return int(vehicle_id)
                    else:
                        print(f"⚠️ No valid Vehicle ID in VIN Decoder response")
                        return None
            else:
                print(f"⚠️ VIN Decoder failed: {response.status_code}")
                return None
        
        # Fallback: if vehicle info dict, extract VIN if available
        elif isinstance(vin_or_vehicle_info, dict):
            vin = vin_or_vehicle_info.get('vin')
            if vin:
                return get_vehicle_id_from_vin(vin)
            else:
                print("⚠️ No VIN found in vehicle info dict")
                return None
        
        return None
        
    except Exception as e:
        print(f"❌ Vehicle ID lookup error: {e}")
        return None

def get_oem_numbers_from_rapidapi_tecdoc(vin: str) -> List[str]:
    """Main workflow to get OEM numbers for a given VIN."""
    
    # NO HARDCODED OEM MAPPINGS - Use dynamic TecDoc API lookup for all VINs
    
    # 0) Persistent VIN cache read (DB). If we have fresh OEMs, use them immediately.
    try:
        cached_vin_oems = get_vin_oem_cache(vin, VIN_DB_CACHE_TTL_SECONDS)
        if cached_vin_oems:
            return cached_vin_oems
    except Exception as _:
        # Cache read failure should not break live lookup
        pass

    vehicle_id = get_vehicle_id_from_vin(vin)
    if not vehicle_id:
        return []

    def _fetch_articles(vehicle_id: int, group_id: int, per_page: int) -> list:
        """Try POST /articles/list-articles first; if non-200, fallback to GET /articles/list/type-id/1/vehicle-id/{}/product-group-id/{}/lang-id/4.
        Returns a raw list of article dicts (unfiltered)."""
        # 1) Try POST list-articles
        try:
            articles_url = f"{CATALOG_BASE_URL}{LIST_ARTICLES_PATH}"
            # NOTE: On RapidAPI, list-articles responds with data when using 'categoryId'
            # whereas 'productGroupId' may return null articles for many accounts/plans.
            # We therefore pass categoryId here for maximum compatibility.
            payload = (
                f"langId={LANG_ID}&countryId={COUNTRY_ID}&typeId={TYPE_ID}"
                f"&vehicleId={vehicle_id}&categoryId={group_id}&page=1&perPage={per_page}"
            )
            print(
                f"   -> list-articles payload: langId={LANG_ID}&countryId={COUNTRY_ID}&typeId={TYPE_ID}"
                f"&vehicleId={vehicle_id}&categoryId={group_id}&page=1&perPage={per_page}"
            )
            headers = {**CATALOG_HEADERS, 'content-type': 'application/x-www-form-urlencoded'}
            resp = requests.post(articles_url, headers=headers, data=payload, timeout=10)
            print(f"   -> Articles API call (POST list-articles) returned status: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, dict):
                    raw_articles = data.get('articles') or (data.get('data') or {}).get('articles')
                    if isinstance(raw_articles, list):
                        print("   -> Using POST list-articles response")
                        return raw_articles
                print(f"   -> Unexpected response format from POST; keys: {list(data.keys()) if isinstance(data, dict) else type(data)}")
        except requests.RequestException as e:
            print(f"   -> POST list-articles exception: {e}")

        # 2) Fallback: GET list/type-id/1/vehicle-id/{vehicle_id}/product-group-id/{group_id}/lang-id/4
        try:
            url = f"{CATALOG_BASE_URL}/articles/list/type-id/{TYPE_ID}/vehicle-id/{vehicle_id}/product-group-id/{group_id}/lang-id/{LANG_ID}"
            print(f"   -> Fallback GET {url}")
            resp = requests.get(url, headers=CATALOG_HEADERS, timeout=8)
            print(f"   -> Articles API call (GET list/type-id) returned status: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, dict):
                    raw_articles = data.get('articles') or (data.get('data') or {}).get('articles')
                    if isinstance(raw_articles, list):
                        print("   -> Using GET list/type-id response")
                        return raw_articles
                print(f"   -> Unexpected response format from GET; keys: {list(data.keys()) if isinstance(data, dict) else type(data)}")
        except requests.RequestException as e:
            print(f"   -> GET list/type-id exception: {e}")
        return []

    all_oems = set()
    
    # 1) Discover shaft-related categories dynamically instead of using hardcoded IDs
    print(f"\n🔍 Discovering shaft-related categories for vehicleId: {vehicle_id}")
    shaft_category_ids = _discover_shaft_category_ids(vehicle_id)
    
    if not shaft_category_ids:
        print("⚠️ No shaft-related categories found, falling back to trying multiple category IDs")
        shaft_category_ids = PRODUCT_GROUP_IDS_TO_TRY
    
    # 2) Loop discovered categories and fetch articles
    for group_id in shaft_category_ids:
        print(f"\n🔍 Searching category ID: {group_id} for vehicleId: {vehicle_id}")
        
        # Fetch articles with POST, fallback to GET if needed
        raw_articles = _fetch_articles(vehicle_id, group_id, PER_PAGE)
        if isinstance(raw_articles, list):
            # FILTER by keywords to ensure we only get shaft-related articles
            # since product group IDs may not be accurate
            sample_names = [
                (x.get('genericArticleName') or x.get('articleProductName') or '')
                for x in raw_articles[:10]
            ]
            print(f"   -> Article names (sample): {sample_names}")
            
            # Filter articles by shaft-related keywords
            articles = []
            for art in raw_articles:
                name = (art.get('genericArticleName') or art.get('articleProductName') or '').strip()
                if _name_allowed(name):
                    articles.append(art)
            
            print(f"   -> Filtered to {len(articles)} shaft-related articles from {len(raw_articles)} total")
            
            print(f"   📦 Found {len(articles)} articles for category {group_id}.")
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
    
    oems_list = list(all_oems)
    # Upsert VIN cache after successful retrieval (even partial set)
    try:
        if oems_list:
            upsert_vin_oem_cache(vin, vehicle_id, oems_list)
    except Exception as _:
        pass
    return oems_list

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
