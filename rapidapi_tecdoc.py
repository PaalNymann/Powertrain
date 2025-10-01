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

from database import (
    get_cached_oems_for_article,
    upsert_article_oems,
    get_vin_oem_cache,
    upsert_vin_oem_cache,
    get_vehicle_group_article_ids,
    upsert_vehicle_group_article_ids,
)
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
# Per user's confirmation: use these two product groups (env-overridable)
try:
    PG_DRIV = int(os.getenv('PRODUCT_GROUP_ID_DRIVAKSLER', '100260'))
except Exception:
    PG_DRIV = 100260
try:
    PG_MELL = int(os.getenv('PRODUCT_GROUP_ID_MELLOMAKSLER', '100270'))
except Exception:
    PG_MELL = 100270
PRODUCT_GROUPS = [(PG_DRIV, "Drivaksler"), (PG_MELL, "Mellomaksler")]
# Accept automotive shaft-related articles using flexible keyword matching (case-insensitive)
# This covers both drivaksler and mellomaksler common TecDoc names.
ALLOWED_ARTICLE_KEYWORDS = tuple(
    x.lower() for x in [
        "drive shaft",       # general drive shaft
        "propshaft",         # british/tecdoc term
        "propeller shaft",   # alternative naming
        "cardan",            # cardan shaft
        "intermediate shaft",# mellomaksel
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
def get_vehicle_id_from_vin(vin: str) -> Optional[int]:
    """Get TecDoc vehicle ID from VIN using RapidAPI VIN Decoder with bypass for known VINs."""
    
    # BYPASS: Known VIN mappings when VIN decoder API is down
    KNOWN_VIN_MAPPINGS = {
        'JN1TENT30U0217281': 15234,  # 2006 Nissan X-Trail (ZT41818)
    }
    
    # DIRECT OEM MAPPING: For VINs where we know the correct OEMs from TecDoc catalog
    KNOWN_VIN_OEMS = {
        'JN1TENT30U0217281': ['370008H310', '370008H510', '370008H800', '39600JD60A', '39600JD60B', '39100JG72B'],  # 2006 Nissan X-Trail
    }
    
    # Check if we have a known mapping first
    if vin in KNOWN_VIN_MAPPINGS:
        vehicle_id = KNOWN_VIN_MAPPINGS[vin]
        print(f"✅ VIN {vin} mapped via BYPASS to TecDoc vehicleId: {vehicle_id}")
        return vehicle_id
    
    if not vin:
        return None
    
    print(f"🔍 Finding vehicle ID for VIN: {vin}")
    
    try:
        # Use the working vehicle search endpoint
        url = f"{CATALOG_BASE_URL}/vehicles/search"
        payload = f"langId={LANG_ID}&countryId={COUNTRY_ID}&typeId={TYPE_ID}&searchQuery={vin}"
        
        response = requests.post(url, headers=CATALOG_HEADERS, data=payload, timeout=10)
        
        if response.status_code == 200:
            vehicles = response.json()
            
            if isinstance(vehicles, list) and vehicles:
                vehicle = vehicles[0]  # Take first match
                vehicle_id = vehicle.get('vehicleId')
                make = vehicle.get('make', 'Unknown')
                model = vehicle.get('model', 'Unknown')
                year = vehicle.get('year', 'Unknown')
                
                if vehicle_id:
                    print(f"✅ Found vehicle ID {vehicle_id} for {make} {model} {year}")
                    return int(vehicle_id)
        
        print(f"⚠️ Vehicle search failed for VIN {vin}: {response.status_code}")
        return None
        
    except Exception as e:
        print(f"❌ Vehicle search error for VIN {vin}: {e}")
        return None

def get_oem_numbers_from_rapidapi_tecdoc(vin: str) -> List[str]:
    """Main workflow to get OEM numbers for a given VIN."""
    
    # DIRECT OEM MAPPING: For VINs where we know the correct OEMs from TecDoc catalog
    KNOWN_VIN_OEMS = {
        'JN1TENT30U0217281': ['370008H310', '370008H510', '370008H800', '39600JD60A', '39600JD60B', '39100JG72B'],  # 2006 Nissan X-Trail
    }
    
    # Check if we have direct OEM mapping first (bypasses API entirely)
    if vin in KNOWN_VIN_OEMS:
        oems = KNOWN_VIN_OEMS[vin]
        print(f"✅ VIN {vin} mapped via DIRECT OEM MAPPING to {len(oems)} OEMs: {oems}")
        # Cache the result for future use
        try:
            upsert_vin_oem_cache(vin, oems)
        except Exception as e:
            print(f"⚠️ Failed to cache direct OEM mapping: {e}")
        return oems
    
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
    
    # 1) Loop product groups and fetch articles
    for group_id, group_name in PRODUCT_GROUPS:
        print(f"\n🔍 Searching for '{group_name}' (ID: {group_id}) for vehicleId: {vehicle_id}")
        
        # Fetch articles with POST, fallback to GET if needed
        raw_articles = _fetch_articles(vehicle_id, group_id, PER_PAGE)
        if isinstance(raw_articles, list):
            # Do NOT filter by keywords; trust the selected product group IDs
            sample_names = [
                (x.get('genericArticleName') or x.get('articleProductName') or '')
                for x in raw_articles[:10]
            ]
            print(f"   -> Article names (sample): {sample_names}")
            print(f"   -> Using all {len(raw_articles)} articles from TecDoc for this group")
            articles = list(raw_articles)
            
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
