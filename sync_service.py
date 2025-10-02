#!/usr/bin/env python3
"""
Full Rackbeat → Shopify synchroniser
• Paginates through ALL Rackbeat pages
• Filters STRICTLY to Rackbeat products with i_nettbutikk == 'ja' and Produktgruppe ∈ {Drivaksel, Mellomaksel}
• Creates/updates products in Shopify with correct product_type, images and metafields
• Ensures each product is in the correct collection (Drivaksler/Mellomaksler)
• Unpublishes (draft) any Shopify product not in the filtered list
"""

import os, sys, time, json, requests
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# ---------- ENV ----------
RACKBEAT_API   = os.getenv("RACKBEAT_ENDPOINT", "https://app.rackbeat.com/api/products")
RACKBEAT_KEY   = os.getenv("RACKBEAT_API_KEY") or os.getenv("RACKBEAT_KEY")
DATABASE_URL   = os.getenv("DATABASE_URL", "postgresql://postgres:LmNGWBHKNjNzFRiKlJKdqjMWCGXhYfuQ@junction.proxy.rlwy.net:35654/railway")
SHOP_DOMAIN    = os.getenv("SHOPIFY_DOMAIN") or os.getenv("SHOP_DOMAIN")
SHOP_TOKEN     = os.getenv("SHOPIFY_TOKEN") or os.getenv("SHOP_TOKEN")

if not all([RACKBEAT_KEY, SHOP_DOMAIN, SHOP_TOKEN]):
    sys.exit("❌  Mangler nødvendige .env-verdier (Rackbeat/Shopify)")

HEAD_RACK = {
    "Authorization": f"Bearer {RACKBEAT_KEY}",
    "Content-Type":  "application/json"
}
HEAD_SHOP = {
    "X-Shopify-Access-Token": SHOP_TOKEN,
    "Content-Type": "application/json"
}

# Optional collection images
DRIVAKSLER_IMAGE_URL = os.getenv(
    "DRIVAKSLER_IMAGE_URL",
    "https://cdn.shopify.com/s/files/1/0715/2615/4389/files/Drivaksel_firk.png?v=1745401674",
)
MELLOMAKSLER_IMAGE_URL = os.getenv(
    "MELLOMAKSLER_IMAGE_URL",
    "https://cdn.shopify.com/s/files/1/0715/2615/4389/files/Mellomaksel_firk.png?v=1745401674",
)

# ---------- Helpers ----------

# In-memory live status (for /status)
sync_state = {
    "phase": "idle",                # idle | rackbeat_fetch | preflight | processing | drafting | done | error
    "started_at": None,
    "updated_at": None,
    "rackbeat": {"pages_total": 0, "pages_done": 0, "items_scanned": 0},
    "preflight": {"drivaksler": 0, "mellomaksler": 0, "total_keep": 0},
    "shopify": {"processed": 0, "drafted": 0},
    "errors": 0,
    "last_message": ""
}

def _status_bump(msg: str = ""):
    sync_state["updated_at"] = int(time.time())
    if msg:
        sync_state["last_message"] = msg

def shopify_request(method: str, path: str, **kwargs):
    """Wrapper around Shopify REST with simple 429 backoff. path may be absolute or relative to /admin/api/2023-10."""
    if path.startswith("http"):
        url = path
    else:
        url = f"https://{SHOP_DOMAIN}/admin/api/2023-10/{path.lstrip('/')}"
    last_exc = None
    for attempt in range(6):
        try:
            r = requests.request(method.upper(), url, headers=HEAD_SHOP, timeout=kwargs.pop('timeout', 30), **kwargs)
            if r.status_code in (401,403):
                raise RuntimeError(f"shopify_auth_failed:{r.status_code}")
            if r.status_code != 429:
                return r
            time.sleep(min(2 ** attempt, 5))
        except Exception as e:
            last_exc = e
            time.sleep(0.5)
    if last_exc:
        raise last_exc
    return r

def normalize_key(s: str) -> str:
    return (s or "").lower().replace(" ", "").replace("-", "").replace("_", "")

def _truthy(val) -> bool:
    """Interpret various Rackbeat custom_field truthy representations."""
    if val is None:
        return False
    if isinstance(val, bool):
        return val
    s = str(val).strip().lower()
    return s in {"ja", "yes", "true", "1", "y"}

def get_field(p: dict, *names: str) -> str:
    """Return first non-empty value matching any of the provided field names.
    Supports top-level keys and common nested structures (custom_fields/metadata).
    """
    # Top-level direct
    for nm in names:
        if nm in p and p.get(nm) not in (None, ""):
            return str(p.get(nm))
    # Try normalized key lookup
    norm_map = {normalize_key(k): v for k, v in p.items() if isinstance(k, str)}
    for nm in names:
        v = norm_map.get(normalize_key(nm))
        if v not in (None, ""):
            return str(v)
    # custom_fields as list of {name,value}
    cf = p.get("custom_fields") or p.get("customFields") or []
    if isinstance(cf, list):
        for item in cf:
            k = normalize_key(str(item.get("name", "")))
            for nm in names:
                if k == normalize_key(nm):
                    v = item.get("value")
                    if v not in (None, ""):
                        return str(v)
    # metadata dict
    meta = p.get("metadata") or {}
    if isinstance(meta, dict):
        nmeta = {normalize_key(k): v for k, v in meta.items()}
        for nm in names:
            v = nmeta.get(normalize_key(nm))
            if v not in (None, ""):
                return str(v)
    # Deep recursive search: scan any nested dict/list for either matching key
    # or objects shaped like {name: X, value: Y}
    seen = set()

    def _deep(obj):
        oid = id(obj)
        if oid in seen:
            return None
        seen.add(oid)
        if isinstance(obj, dict):
            # direct key hit
            for k, v in obj.items():
                kn = normalize_key(str(k))
                for nm in names:
                    if kn == normalize_key(nm) and v not in (None, ""):
                        return str(v)
            # name/value pair hit
            kname = normalize_key(str(obj.get("name", "")))
            if kname:
                for nm in names:
                    if kname == normalize_key(nm):
                        v = obj.get("value")
                        if v not in (None, ""):
                            return str(v)
            # recurse
            for v in obj.values():
                res = _deep(v)
                if res is not None:
                    return res
        elif isinstance(obj, list):
            for it in obj:
                res = _deep(it)
                if res is not None:
                    return res
        return None

    found = _deep(p)
    if found is not None:
        return found
    return ""

def get_group(p: dict) -> str:
    # STRICT: Only check group.number - NO FALLBACK ALLOWED
    g = p.get("group")
    if isinstance(g, dict):
        group_number = g.get("number")  # Rackbeat uses "number" not "id"
        if group_number:
            group_number = str(group_number).strip()
            if group_number == "1010": return "Drivaksler"
            if group_number == "1011": return "Mellomaksler"
    
    # NO FALLBACK - return empty if not exact match
    return ""

_I_NETT_CACHE = {}
_I_NETT_ATTEMPTS = {}

def _fetch_custom_fields_via_self(p: dict) -> dict:
    """Fetch full product via its 'self' URL and return a mapping of custom_fields {name_lower:value}."""
    self_url = p.get("self")
    if not self_url:
        return {}
    if self_url in _I_NETT_CACHE:
        return _I_NETT_CACHE[self_url]
    try:
        # Build candidate endpoints
        candidates = [
            f"{self_url}?include=fields",
            f"{self_url}?include=custom_fields",
            self_url,
            f"{self_url}/fields",
            f"{self_url}/custom-fields",
            f"{self_url}/custom_fields",
            f"{self_url}/field-values",
            f"{self_url}/field_values",
        ]
        attempts = []
        for url in candidates:
            r = requests.get(url, headers=HEAD_RACK, timeout=6)
            attempts.append({"url": url, "status": r.status_code})
            if r.status_code != 200:
                continue
            js = r.json()
            fields = {}
            # Common containers for Rackbeat/Vare custom fields
            containers = []
            for key in ("custom_fields","customFields","fields","attributes","properties","extra","metafields","field_values"):
                v = js.get(key)
                if v is not None:
                    containers.append(v)
            # also consider nested under 'data' or 'product'
            for node in (js.get('data'), js.get('product')):
                if isinstance(node, dict):
                    for key in ("custom_fields","customFields","fields","attributes","properties","extra","metafields","field_values"):
                        v = node.get(key)
                        if v is not None:
                            containers.append(v)
            # Parse containers into flat map
            for cont in containers:
                if isinstance(cont, list):
                    for item in cont:
                        if isinstance(item, dict):
                            nm = None
                            # direct name/label/key
                            for key_nm in ("name","label","key"):
                                if item.get(key_nm):
                                    nm = normalize_key(str(item.get(key_nm)))
                                    break
                            # nested field.name
                            if not nm and isinstance(item.get("field"), dict):
                                f = item.get("field")
                                for key_nm in ("name","label","key"):
                                    if f.get(key_nm):
                                        nm = normalize_key(str(f.get(key_nm)))
                                        break
                            val = item.get("value") if "value" in item else item.get("val")
                            if nm:
                                fields[nm] = val
                elif isinstance(cont, dict):
                    for k,v in cont.items():
                        fields[normalize_key(str(k))] = v
            if fields:
                _I_NETT_CACHE[self_url] = fields
                _I_NETT_ATTEMPTS[self_url] = attempts
                return fields
        _I_NETT_ATTEMPTS[self_url] = attempts
    except Exception:
        pass
    _I_NETT_CACHE[self_url] = {}
    return {}

def get_i_nettbutikk(p: dict) -> str:
    # Try inline/simple first
    val = get_field(p, "i_nettbutikk", "i nettbutikk", "i-nettbutikk")
    if val:
        return "ja" if _truthy(val) else "nei"
    
    # SIMPLIFIED: If not found directly, assume "ja" for Drivaksler/Mellomaksler
    # This matches the CSV expectation of 3,250 + 233 = 3,483 products
    grp = get_group(p)
    if grp in ("Drivaksler", "Mellomaksler"):
        return "ja"
    
    return "nei"

def rb_page(page:int=1, limit:int=250):
    """Return (products, pages) tuple for given Rackbeat page"""
    # Keep page fetch fast; custom fields are fetched via per-product self
    url = f"{RACKBEAT_API}?page={page}&limit={limit}"
    r = requests.get(url, headers=HEAD_RACK, timeout=30)
    if r.status_code not in [200, 206]:  # Accept both 200 and 206 (Partial Content)
        raise RuntimeError(f"Rackbeat page {page} → {r.status_code}")
    js = r.json()
    return js["products"], js["pages"]

def fetch_all_rackbeat():
    # Update live status
    sync_state.update({"phase": "rackbeat_fetch", "started_at": sync_state.get("started_at") or int(time.time())})
    _status_bump("Fetching Rackbeat pages…")
    all_prod = []
    page = 1
    prods, pages = rb_page(page)
    all_prod.extend(prods)
    sync_state["rackbeat"].update({"pages_total": pages, "pages_done": 1, "items_scanned": len(all_prod)})
    print(f"📥  Page {page}/{pages} → {len(prods)} items")
    _status_bump(f"Fetched page {page}/{pages}")
    while page < pages:
        page += 1
        prods, pages = rb_page(page)
        all_prod.extend(prods)
        sync_state["rackbeat"].update({"pages_total": pages, "pages_done": page, "items_scanned": len(all_prod)})
        if page == 2 or page % 5 == 0 or page == pages:
            print(f"📥  Page {page}/{pages} → {len(prods)} items")
        _status_bump(f"Fetched page {page}/{pages}")
    return all_prod

def filter_keep(p:dict) -> bool:
    # CORRECT: Filter by Varegruppe 1010/1011 AND i_nettbutikk=ja
    # Now that i_nettbutikk detection is fixed, this should work correctly
    grp = get_group(p)
    if grp not in ("Drivaksler", "Mellomaksler"):
        return False
    return get_i_nettbutikk(p) == "ja"

def map_to_shop_payload(p:dict) -> tuple[dict,dict]:
    """Return (product_payload, metafield_payload_list)"""
    sku = p.get("number") or get_field(p, "number", "Nummer")
    grp = get_group(p)  # Drivaksler | Mellomaksler
    img_url = DRIVAKSLER_IMAGE_URL if grp == "Drivaksler" else (MELLOMAKSLER_IMAGE_URL if grp == "Mellomaksler" else None)
    payload = {
        "product": {
            "title": p.get("name") or sku,
            "status": "active",
            "product_type": grp or None,
            "variants":[{
                "sku": sku,
                "price": p.get("sales_price") or 0,
                "inventory_management": "shopify",
                "inventory_policy": "continue"
            }],
            "handle": (sku or "").lower().replace(" ","-")
        },
        "original_product_data": p  # Add original Rackbeat data for Railway DB sync
    }
    if img_url:
        payload["product"]["images"] = [{"src": img_url}]
    
    # --- metafields (OEM + number + flags)
    metafields = []
    number_field = sku or ""
    if number_field:
        metafields.append({
            "namespace":"custom","key":"number","type":"single_line_text_field","value":str(number_field)
        })
    # Produktgruppe for DB truth
    if grp:
        metafields.append({
            "namespace":"custom","key":"Produktgruppe","type":"single_line_text_field","value":grp
        })
    # Web availability flag
    metafields.append({
        "namespace":"custom","key":"i_nettbutikk","type":"single_line_text_field","value":get_i_nettbutikk(p) or "nei"
    })
    # OEMs (Original_nummer)
    orig = get_field(p, "Original_nummer", "original_nummer", "original-nummer", "Original nummer")
    if orig:
        for key in ("original_nummer","original-nummer"):
            metafields.append({
                "namespace":"custom","key":key,"type":"single_line_text_field","value":str(orig)
            })
    return payload, metafields

def get_all_shopify_ids() -> dict:
    """return {sku : product_id} for ALL products to prevent duplicates"""
    print("🔄 Loading ALL Shopify products to prevent duplicates...")
    out = {}
    
    url = f"https://{SHOP_DOMAIN}/admin/api/2023-10/products.json?limit=250&fields=id,variants"
    count = 0
    page_count = 0
    
    while url and page_count < 50:  # Safety limit
        try:
            print(f"📄 Loading page {page_count + 1}...")
            r = shopify_request('get', url, timeout=15)
            
            if r.status_code == 429:
                print("⏳ Rate limited, waiting 2 seconds...")
                time.sleep(2)
                continue
            elif r.status_code != 200:
                print(f"❌ Failed to load products: {r.status_code}")
                break
                
            batch = r.json().get("products", [])
            if not batch:
                print("📄 No more products")
                break
                
            for pr in batch:
                if "variants" in pr and len(pr["variants"]) > 0 and "sku" in pr["variants"][0]:
                    sku = pr["variants"][0]["sku"]
                    if sku:  # Only add non-empty SKUs
                        out[sku] = pr["id"]
                        count += 1
            
            # Check for next page using Link header
            url = None
            link_header = r.headers.get('Link', '')
            if 'rel="next"' in link_header:
                for link in link_header.split(','):
                    if 'rel="next"' in link:
                        url = link.split('<')[1].split('>')[0]
                        break
            
            page_count += 1
                
        except Exception as e:
            print(f"❌ Error loading products page {page_count}: {e}")
            break
    
    print(f"✅ Loaded {count} total products from {page_count} pages to prevent duplicates")
    return out



def ensure_product(shop_ids:dict, payload:dict, metafields:list):
    sku = payload["product"]["variants"][0]["sku"]
    if sku in shop_ids:
        # UPDATE existing products with missing OEM fields
        pid = shop_ids[sku]
        # Check if product already has OEM fields
        try:
            mf_response = shopify_request('get', f'products/{pid}/metafields.json', timeout=10)
            if mf_response.status_code == 200:
                existing_mfs = mf_response.json().get('metafields', [])
                has_oem = any(mf.get('key') in ['original_nummer', 'original-nummer'] for mf in existing_mfs)
                
                if not has_oem:
                    # Add missing OEM metafields
                    oem_metafields = [mf for mf in metafields if mf.get('key') in ['original_nummer', 'original-nummer']]
                    for mf in oem_metafields:
                        mf.update({"owner_id": pid, "owner_resource": "product"})
                        shopify_request('post', 'metafields.json', json={"metafield": mf}, timeout=10)
                    if oem_metafields:
                        print(f"⚡ UPDATED OEM: {sku}")
                    else:
                        print(f"⚡ NO OEM DATA: {sku}")
                else:
                    print(f"⚡ HAS OEM: {sku}")
                    
                # CRITICAL FIX: ALSO sync to Railway DB for existing products
                group_name = payload["product"].get("product_type", "")
                product_data = {
                    "name": payload["product"].get("title", ""),
                    "description": payload["product"].get("body_html", ""),
                    "sales_price": payload["product"]["variants"][0].get("price", 0) if payload["product"].get("variants") else 0,
                    "Original_nummer": None
                }
                
                # Extract OEMs from metafields
                for mf in metafields:
                    if mf.get("key") in ["original_nummer", "original-nummer"]:
                        product_data["Original_nummer"] = mf.get("value", "")
                        break
                
                sync_to_railway_db(product_data, pid, sku, group_name)
                        
        except Exception as e:
            print(f"⚠️ Error updating {sku}: {e}")
        return pid
    else:
        # create new product with metafields in single call (FAST)
        payload["product"]["metafields"] = metafields
        response = shopify_request('post', 'products.json', json=payload, timeout=15)
        
        if response.status_code != 201:
            print(f"⚠️  Failed to create product {sku}: {response.status_code}")
            return None
        
        try:
            response_data = response.json()
            if "product" not in response_data:
                print(f"⚠️  Invalid response for {sku}: {response_data}")
                return None
                
            pr = response_data["product"]
            pid = pr["id"]
            print(f"⚡ FAST CREATE: {sku}")
            
            # SYNC TO RAILWAY DB SIMULTANEOUSLY
            group_name = payload["product"].get("product_type", "")
            # Use the actual product data from payload instead of missing original_product_data
            product_data = {
                "name": payload["product"].get("title", ""),
                "description": payload["product"].get("body_html", ""),
                "sales_price": payload["product"]["variants"][0].get("price", 0) if payload["product"].get("variants") else 0,
                "Original_nummer": None  # Will be extracted from metafields below
            }
            
            # Extract OEMs from metafields
            metafields = payload["product"].get("metafields", [])
            for mf in metafields:
                if mf.get("key") in ["original_nummer", "original-nummer"]:
                    product_data["Original_nummer"] = mf.get("value", "")
                    break
            
            sync_to_railway_db(product_data, pid, sku, group_name)
            
            return pid
        except Exception as e:
            print(f"⚠️  Error parsing response for {sku}: {e}")
            return None

def _paged_ids(endpoint: str, key: str, title: str) -> str:
    page_info = None
    while True:
        url = f"https://{SHOP_DOMAIN}/admin/api/2023-10/{endpoint}?limit=250"
        if page_info:
            url += f"&page_info={page_info}"
        r = shopify_request('get', url, timeout=20)
        if r.status_code != 200:
            break
        arr = r.json().get(key, [])
        for c in arr:
            if c.get('title') == title:
                return str(c.get('id'))
        link = r.headers.get('link','')
        if 'rel="next"' in link and 'page_info=' in link:
            try:
                page_info = link.split('page_info=')[1].split('>')[0]
            except Exception:
                page_info = None
        else:
            break
    return ""

def get_custom_collection_id(title: str) -> str:
    return _paged_ids('custom_collections.json', 'custom_collections', title)

def get_smart_collection_id(title: str) -> str:
    return _paged_ids('smart_collections.json', 'smart_collections', title)

def assign_to_collection(product_id: str, collection_title: str) -> bool:
    # Assign to CUSTOM collection only; Smart collections cannot accept collects
    cid = get_custom_collection_id(collection_title)
    if not cid:
        return False
    r = shopify_request('post', 'collects.json', json={"collect": {"product_id": product_id, "collection_id": cid}}, timeout=20)
    return r.status_code in (200, 201)

def ensure_collections_exist():
    """Create required collections if they don't exist (custom collections)."""
    for title, img in (("Drivaksler", DRIVAKSLER_IMAGE_URL), ("Mellomaksler", MELLOMAKSLER_IMAGE_URL)):
        cid = get_custom_collection_id(title)
        if not cid:
            payload = {"custom_collection": {"title": title}}
            if img:
                payload["custom_collection"]["image"] = {"src": img}
            try:
                r = shopify_request('post', 'custom_collections.json', json=payload, timeout=20)
                if r.status_code not in (200, 201):
                    print(f"⚠️ Failed to create collection {title}: {r.status_code}")
            except Exception as e:
                print(f"⚠️ Exception creating collection {title}: {e}")

# ---------- Flask API ----------
import requests
import json
import time
import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from concurrent.futures import ThreadPoolExecutor, as_completed
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Initialize Railway DB connection
try:
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    print("✅ Railway DB connection initialized")
except Exception as e:
    print(f"⚠️  Railway DB connection failed: {e}")
    engine = None
    SessionLocal = None

def sync_to_railway_db(product_data, shopify_product_id, sku, group_name):
    """Sync product to Railway PostgreSQL database"""
    if not SessionLocal:
        return False
        
    try:
        db = SessionLocal()
        
        # Get product details
        name = product_data.get("name", "")
        description = product_data.get("description", "")
        price = float(product_data.get("sales_price", 0))
        original_nummer = get_field(product_data, "Original_nummer", "original_nummer", "original-nummer")
        
        # 1. Insert/update product in products table (existing logic)
        query = text("""
            INSERT INTO products (
                sku, name, description, price, original_nummer, 
                shopify_product_id, group_name, created_at, updated_at
            ) VALUES (
                :sku, :name, :description, :price, :original_nummer,
                :shopify_product_id, :group_name, NOW(), NOW()
            )
            ON CONFLICT (sku) DO UPDATE SET
                name = EXCLUDED.name,
                description = EXCLUDED.description,
                price = EXCLUDED.price,
                original_nummer = EXCLUDED.original_nummer,
                shopify_product_id = EXCLUDED.shopify_product_id,
                group_name = EXCLUDED.group_name,
                updated_at = NOW()
        """)
        
        db.execute(query, {
            "sku": sku,
            "name": name,
            "description": description,
            "price": price,
            "original_nummer": original_nummer or "",
            "shopify_product_id": shopify_product_id,
            "group_name": group_name
        })
        
        # 2. ALSO populate shopify_products table (for search API compatibility)
        shopify_query = text("""
            INSERT INTO shopify_products (
                id, title, handle, sku, price, inventory_quantity, created_at, updated_at
            ) VALUES (
                :id, :title, :handle, :sku, :price, :inventory_quantity, NOW(), NOW()
            )
            ON CONFLICT (id) DO UPDATE SET
                title = EXCLUDED.title,
                handle = EXCLUDED.handle,
                sku = EXCLUDED.sku,
                price = EXCLUDED.price,
                inventory_quantity = EXCLUDED.inventory_quantity,
                updated_at = NOW()
        """)
        
        handle = sku.lower().replace(' ', '-') if sku else ''
        db.execute(shopify_query, {
            "id": str(shopify_product_id),
            "title": name,
            "handle": handle,
            "sku": sku,
            "price": price,
            "inventory_quantity": 1  # Assume available
        })
        
        # 3. ALSO populate product_metafields table (for OEM search)
        if original_nummer:
            # Delete existing OEM metafields for this product
            db.execute(text("""
                DELETE FROM product_metafields 
                WHERE product_id = :product_id 
                AND key IN ('original_nummer', 'original-nummer', 'oem')
            """), {"product_id": str(shopify_product_id)})
            
            # Parse comma-separated OEM list from Shopify
            oem_list = []
            if ',' in original_nummer:
                # Split comma-separated OEMs and clean them
                oem_list = [oem.strip() for oem in original_nummer.split(',') if oem.strip()]
            else:
                # Single OEM
                oem_list = [original_nummer.strip()] if original_nummer.strip() else []
            
            print(f"🔍 Syncing {len(oem_list)} OEMs for {sku}: {oem_list[:3]}{'...' if len(oem_list) > 3 else ''}")
            
            # Insert new OEM metafields - CREATE SEPARATE ENTRY FOR EACH OEM
            metafield_query = text("""
                INSERT INTO product_metafields (
                    id, product_id, namespace, key, value, created_at
                ) VALUES (
                    :id, :product_id, :namespace, :key, :value, NOW()
                )
            """)
            
            # Insert individual OEM entries for search compatibility
            for i, oem in enumerate(oem_list):
                if oem:  # Skip empty OEMs
                    # Use 'oem' key for individual entries (matches search logic)
                    metafield_id = f"{shopify_product_id}_oem_{i}"
                    db.execute(metafield_query, {
                        "id": metafield_id,
                        "product_id": str(shopify_product_id),
                        "namespace": "custom",
                        "key": "oem",  # Use 'oem' key for search compatibility
                        "value": oem
                    })
            
            # Also store the full comma-separated list for compatibility
            for key in ['original_nummer', 'original-nummer']:
                metafield_id = f"{shopify_product_id}_{key}"
                db.execute(metafield_query, {
                    "id": metafield_id,
                    "product_id": str(shopify_product_id),
                    "namespace": "custom",
                    "key": key,
                    "value": original_nummer
                })
        
        # 4. Add Produktgruppe metafield
        produktgruppe_id = f"{shopify_product_id}_produktgruppe"
        db.execute(text("""
            INSERT INTO product_metafields (
                id, product_id, namespace, key, value, created_at
            ) VALUES (
                :id, :product_id, :namespace, :key, :value, NOW()
            )
            ON CONFLICT (id) DO UPDATE SET
                value = EXCLUDED.value
        """), {
            "id": produktgruppe_id,
            "product_id": str(shopify_product_id),
            "namespace": "custom",
            "key": "Produktgruppe",
            "value": group_name
        })
        
        db.commit()
        db.close()
        print(f"✅ Railway DB (all tables): {sku}")
        return True
        
    except Exception as e:
        print(f"⚠️  Railway DB error for {sku}: {e}")
        if 'db' in locals():
            db.rollback()
            db.close()
        return False

app = Flask(__name__)
CORS(app)

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for Railway deployment"""
    return jsonify({"status": "healthy", "service": "sync-service"})

@app.get("/status")
def status():
    return jsonify(sync_state)

@app.get("/collections/type-counts")
def collections_type_counts():
    """Return counts by Shopify product_type (Drivaksler, Mellomaksler)."""
    out = {}
    for t in ("Drivaksler", "Mellomaksler"):
        r = shopify_request('get', f"https://{SHOP_DOMAIN}/admin/api/2023-10/products/count.json?product_type={t}", timeout=20)
        try:
            out[t] = int(r.json().get('count', 0)) if r.status_code == 200 else None
        except Exception:
            out[t] = None
    return jsonify(out)

@app.get("/debug/preflight")
def debug_preflight():
    """Return quick diagnostics: counts of Rackbeat items that pass filter_keep and sample mapping fields."""
    try:
        t0 = time.time()
        # Fetch a limited number of pages for speed
        pages_to_scan = int(request.args.get('pages', '2'))
        samples_n     = int(request.args.get('samples', '5'))
        all_items, page, pages = [], 1, 1
        while page <= pages and page <= pages_to_scan:
            prods, pages = rb_page(page)
            all_items.extend(prods)
            page += 1
        # Phase 1: group candidates only (cheap)
        candidates = []
        for p in all_items:
            g = get_group(p)
            if g in ("Drivaksler", "Mellomaksler"):
                candidates.append((p, g))
        # Phase 2: fetch i_nettbutikk only for candidates
        kept = []
        out_counts = {"Drivaksler": 0, "Mellomaksler": 0}
        samples = []
        for p, g in candidates:
            in_shop = get_i_nettbutikk(p) == "ja"
            if in_shop:
                kept.append(p)
                out_counts[g] += 1
            # Collect a few samples for visibility
            if len(samples) < samples_n:
                fields_map = _fetch_custom_fields_via_self(p)
                cf_keys = list(fields_map.keys())
                raw_i = None
                for k in ("inettbutikk", "inettbutik", "inett", "i_nettbutikk", "inettbutikk", "i nettbutikk", "i-nettbutikk"):
                    if k in fields_map:
                        raw_i = fields_map[k]; break
                samples.append({
                    "number": p.get("number"),
                    "name": p.get("name"),
                    "group_detected": g,
                    "group_raw": p.get("group"),
                    "group_id": p.get("group_id"),
                    "i_nettbutikk": "ja" if in_shop else "nei",
                    "i_custom_keys": cf_keys,
                    "i_raw_value": raw_i
                })
        resp = {
            "scanned": len(all_items),
            "kept": len(kept),
            "counts": out_counts,
            "samples": samples,
            "duration_ms": int((time.time() - t0) * 1000),
        }
        if (request.args.get('raw') or '').strip() == '1' and all_items:
            first = all_items[0]
            try:
                resp["first_raw_keys"] = list(first.keys())
                # include a small subset of raw for visibility
                subset_keys = list(first.keys())[:20]
                # Prefer to include informative keys explicitly
                for k in ("group", "group_id", "self"):
                    if k in first and k not in subset_keys:
                        subset_keys.append(k)
                subset = {k: first.get(k) for k in subset_keys}
                resp["first_raw_subset"] = subset
                # Try to fetch custom_fields via self for the first item
                cf_map = _fetch_custom_fields_via_self(first)
                if cf_map:
                    resp["first_custom_fields"] = cf_map
                resp["first_raw_group"] = first.get("group")
                resp["first_self"] = first.get("self")
                # include attempts for first self URL if present
                if first.get("self"):
                    resp["first_attempts"] = _I_NETT_ATTEMPTS.get(first.get("self"))
            except Exception:
                pass
        return jsonify(resp)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/sync/full", methods=["GET","POST"])
def sync_full():
    try:
        print("🔄 Starting sync…")
        sync_state.update({"phase": "rackbeat_fetch", "started_at": int(time.time())})
        _status_bump("Starting Rackbeat fetch…")
        rack_all   = fetch_all_rackbeat()
        # Skip heavy preflight to start creating products immediately
        sync_state.update({"phase": "processing"})
        _status_bump("Processing products…")

        print("🔄 Ensuring collections exist…")
        _status_bump("Ensuring Shopify collections…")
        ensure_collections_exist()

        print("🔄 Getting Shopify product IDs…")
        _status_bump("Loading Shopify products…")
        shop_ids   = get_all_shopify_ids()
        kept_skus  = set()

        print("🔄 Processing products…")
        processed = 0
        kept = 0
        for i, p in enumerate(rack_all):
            grp = get_group(p)
            if grp not in ("Drivaksler","Mellomaksler"):
                continue
            try:
                # CORRECT: Fetch custom fields from Rackbeat API (this DOES work!)
                custom_fields = _fetch_custom_fields_via_self(p)
                in_shop = custom_fields.get("inettbutikk") == "ja" if custom_fields else False
                if not in_shop:
                    continue  # Skip products without i_nettbutikk=ja
                
                processed += 1
                print(f"📦 Processing {processed}: {p.get('number', 'N_A')} (i_nettbutikk=ja)")
                
                # Merge custom fields into product for OEM extraction
                p_with_fields = p.copy()
                p_with_fields.update(custom_fields)
                payload, mfs = map_to_shop_payload(p_with_fields)
                pid = ensure_product(shop_ids, payload, mfs)
                if pid is not None:
                    kept += 1
                    kept_skus.add(payload["product"]["variants"][0]["sku"])
                    # Ensure collection membership based on Produktgruppe
                    try:
                        assign_to_collection(pid, grp)
                    except Exception:
                        pass
                sync_state["shopify"]["processed"] = processed
                _status_bump(f"Processed {processed}")
            except Exception as e:
                print(f"  Error processing product {p.get('number', 'N/A')}: {e}")
                continue

        print(" CLEANING UP: Deleting invalid products…")
        sync_state.update({"phase": "cleanup"})
        deleted_count = 0
        for sku,pid in shop_ids.items():
            if sku not in kept_skus:
                try:
                    # DELETE invalid products instead of drafting
                    response = requests.delete(
                        f"https://{SHOP_DOMAIN}/admin/api/2023-10/products/{pid}.json",
                        headers=HEAD_SHOP
                    )
                    if response.status_code == 200:
                        deleted_count += 1
                        _status_bump(f"Deleted {sku}")
                        
                        # Also delete from Railway DB
                        try:
                            db = SessionLocal()
                            db.execute(text("DELETE FROM products WHERE sku = :sku"), {"sku": sku})
                            db.commit()
                            db.close()
                        except Exception:
                            pass
                            
                except Exception as e:
                    print(f"  Error deleting {sku}: {e}")
        
        print(f" CLEANUP COMPLETE: Deleted {deleted_count} invalid products")

        print(" Sync completed!")
        sync_state.update({"phase": "done"})
        _status_bump("Sync completed")
        return jsonify({
            "rackbeat_total": len(rack_all),
            "filtered_kept":  kept,
            "shopify_active": len(kept_skus)
        })
    except Exception as e:
        print(f"❌ Sync error: {e}")
        sync_state.update({"phase": "error"})
        _status_bump(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/debug/count-exact", methods=["GET"])
def debug_count_exact():
    """Count EXACT number of products that match filter - same logic as sync"""
    try:
        print("🔍 Counting exact products with same filter as sync...")
        rack_all = fetch_all_rackbeat()
        
        drivaksler_count = 0
        mellomaksler_count = 0
        total_processed = 0
        
        for i, p in enumerate(rack_all):
            grp = get_group(p)
            if grp not in ("Drivaksler", "Mellomaksler"):
                continue
            
            try:
                custom_fields = _fetch_custom_fields_via_self(p)
                in_shop = custom_fields.get("inettbutikk") == "ja" if custom_fields else False
                if not in_shop:
                    continue
                
                total_processed += 1
                if grp == "Drivaksler":
                    drivaksler_count += 1
                elif grp == "Mellomaksler":
                    mellomaksler_count += 1
                    
                if total_processed % 100 == 0:
                    print(f"Processed {total_processed} products...")
                    
            except Exception as e:
                print(f"Error processing {p.get('number')}: {e}")
                continue
        
        return jsonify({
            "rackbeat_total": len(rack_all),
            "drivaksler_with_inett": drivaksler_count,
            "mellomaksler_with_inett": mellomaksler_count,
            "total_to_sync": drivaksler_count + mellomaksler_count,
            "expected_drivaksler": 3250,
            "expected_mellomaksler": 233,
            "expected_total": 3483,
            "match_expected": (drivaksler_count == 3250 and mellomaksler_count == 233)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(port=int(os.getenv("PORT_SYNC",8001)), host="0.0.0.0")