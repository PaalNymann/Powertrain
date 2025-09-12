#!/usr/bin/env python3
"""
Full Rackbeat → Shopify synchroniser
• Paginates through ALL Rackbeat pages
• Filters to products that have stock & price
• Creates/updates products in Shopify
• Writes/updates required metafields
• Unpublishes (draft) any Shopify product not in the filtered list
"""

import os, sys, time, json, requests
from dotenv import load_dotenv
load_dotenv()

# Import database functions
from database import SessionLocal, ShopifyProduct, ProductMetafield, init_db
from datetime import datetime

# ---------- ENV ----------
RACKBEAT_API   = os.getenv("RACKBEAT_ENDPOINT", "https://app.rackbeat.com/api/products")
RACKBEAT_KEY   = os.getenv("RACKBEAT_API_KEY")
SHOP_DOMAIN    = os.getenv("SHOPIFY_DOMAIN")
SHOP_TOKEN     = os.getenv("SHOPIFY_TOKEN")
# Runtime guards
SYNC_HARD_TIMEOUT_SECONDS = int(os.getenv("SYNC_HARD_TIMEOUT_SECONDS", "900"))  # 15 minutes hard stop
RACKBEAT_MAX_PAGES = int(os.getenv("RACKBEAT_MAX_PAGES", "100"))  # safety guard

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

# ---------- Helpers ----------

def find_variant_by_sku(sku: str):
    """Find an existing variant by SKU. Returns dict with product_id and variant_id, or None."""
    try:
        url = f"https://{SHOP_DOMAIN}/admin/api/2023-10/variants.json?sku={requests.utils.quote(sku)}"
        r = requests.get(url, headers=HEAD_SHOP, timeout=20)
        if r.status_code != 200:
            return None
        variants = r.json().get("variants", [])
        if not variants:
            return None
        v = variants[0]
        return {"product_id": v.get("product_id"), "variant_id": v.get("id")}
    except Exception:
        return None

def rb_page(page:int=1, limit:int=250):
    """Return (products, pages) tuple for given Rackbeat page"""
    # Include metadata in fields parameter to get custom fields
    params = {
        "limit": limit,
        "page": page,
        "fields": "number,name,sales_price,available_quantity,group,metadata"
    }
    r = requests.get(RACKBEAT_API, headers=HEAD_RACK, params=params, timeout=30)
    if r.status_code not in [200, 206]:  # Accept both 200 and 206 (Partial Content)
        raise RuntimeError(f"Rackbeat page {page} → {r.status_code}")
    js = r.json()
    return js["products"], js["pages"]

def fetch_all_rackbeat() -> list[dict]:
    """Download every Rackbeat product page-by-page (bounded by RACKBEAT_MAX_PAGES)."""
    all_prod, page, pages = [], 1, 1
    while page <= pages and page <= RACKBEAT_MAX_PAGES:
        prods, pages = rb_page(page)
        print(f"📥  Page {page}/{pages} → {len(prods)} items")
        all_prod.extend(prods)
        page += 1
    if page > RACKBEAT_MAX_PAGES:
        print(f"⚠️  Stopped fetching after {RACKBEAT_MAX_PAGES} pages (safety guard)")
    return all_prod

def filter_keep(p:dict) -> bool:
    """Filter products to keep only those that should be synced to Shopify"""
    # Check product group - ONLY Drivaksel and Mellomaksel
    group_name = p.get("group", {}).get("name", "")
    if group_name not in ["Drivaksel", "Mellomaksel"]:
        return False
    
    # Check i_nettbutikk field (webshop availability) - CRITICAL FILTER
    # USER REQUIREMENT: All products with i_nettbutikk: ja should be included regardless of stock
    i_nettbutikk = extract_custom_field(p, "i_nettbutikk").lower()
    if i_nettbutikk != "ja":
        print(f"🚫 FILTERED OUT: '{p.get('name', 'N/A')[:30]}' - i_nettbutikk: '{i_nettbutikk}' (Group: {group_name})")
        return False
    
    print(f"✅ KEEPING: '{p.get('name', 'N/A')[:50]}' (Group: {group_name}, Stock: {p.get('available_quantity', 0)}, Price: {p.get('sales_price', 0)})")
    return True

def unpublish_nonkept_products(kept_skus:set, product_types:list[str]=["Drivaksler","Mellomaksler"]):
    """Set status=draft for products in the given product_types whose primary variant SKU is not in kept_skus.
    This removes duplicates and products that no longer meet filter rules.
    """
    try:
        for ptype in product_types:
            page_info = None
            while True:
                url = f"https://{SHOP_DOMAIN}/admin/api/2023-10/products.json?limit=250&product_type={ptype}"
                if page_info:
                    url += f"&page_info={page_info}"
                r = requests.get(url, headers=HEAD_SHOP, timeout=30)
                if r.status_code != 200:
                    print(f"   ⚠️ Failed listing products for cleanup ({ptype}): {r.status_code}")
                    break
                data = r.json().get("products", [])
                if not data:
                    break
                for pr in data:
                    variants = pr.get("variants", [])
                    sku = variants[0].get("sku") if variants else None
                    pid = pr.get("id")
                    if sku and pid and sku not in kept_skus:
                        try:
                            resp = requests.put(
                                f"https://{SHOP_DOMAIN}/admin/api/2023-10/products/{pid}.json",
                                headers=HEAD_SHOP,
                                json={"product": {"id": pid, "status": "draft"}},
                                timeout=20,
                            )
                            if resp.status_code == 200:
                                print(f"   🗑️ Unpublished non-kept product (SKU: {sku}, ID: {pid})")
                            else:
                                print(f"   ⚠️ Unpublish failed for {pid} ({resp.status_code})")
                        except Exception as e:
                            print(f"   ⚠️ Unpublish exception for {pid}: {e}")
                # pagination
                link = r.headers.get("link", "")
                if 'rel="next"' in link and "page_info=" in link:
                    try:
                        page_info = link.split("page_info=")[1].split(">")[0]
                    except Exception:
                        page_info = None
                else:
                    break
    except Exception as e:
        print(f"   ⚠️ Cleanup error: {e}")

def get_original_nummer_from_metadata(metadata):
    """Extract Original_nummer from metadata array"""
    for field in metadata:
        if field.get('slug') == 'original-nummer':
            return field.get('value', '')
    return ''

def get_i_nettbutikk_from_metadata(metadata):
    """Extract i_nettbutikk from metadata array"""
    # Test different possible slug names (case-insensitive)
    possible_slugs = ['i-nettbutikk', 'i_nettbutikk', 'nettbutikk', 'webshop', 'online']
    for field in metadata:
        slug = field.get('slug', '').lower()  # Convert to lowercase for comparison
        if slug in possible_slugs:
            value = field.get('value', '').lower().strip()  # Also normalize value
            return value
    return ''

def debug_metadata_fields(p):
    """Debug function to show all metadata fields"""
    metadata = p.get('metadata', [])
    print(f"🔍 Metadata felter for produkt: {p.get('name', '')[:50]}")
    for field in metadata:
        print(f"   Slug: {field.get('slug')} = Value: {field.get('value')}")
    return metadata

def extract_custom_field(p:dict, field_name:str) -> str:
    """Extract custom field from product metadata array"""
    metadata = p.get('metadata', [])
    
    if field_name == "Original_nummer":
        return get_original_nummer_from_metadata(metadata)
    elif field_name == "i_nettbutikk":
        return get_i_nettbutikk_from_metadata(metadata)
    else:
        # For other fields, search by slug
        for field in metadata:
            if field.get('slug') == field_name.lower().replace('_', '-'):
                return field.get('value', '')
    
    return ""

def map_to_shop_payload(p:dict) -> tuple[dict,dict]:
    """Return (product_payload, metafield_payload_list)"""
    sku = p["number"]
    
    # Map Rackbeat group to Shopify collection (plural forms)
    group_name = p.get("group", {}).get("name", "")
    collection_mapping = {
        "Drivaksel": "Drivaksler",
        "Mellomaksel": "Mellomaksler"
    }
    shopify_collection = collection_mapping.get(group_name, "Uncategorized")
    
    payload = {
        "product": {
            "title": p["name"] or sku,
            "status": "active",
            "product_type": shopify_collection,
            "variants": [{
                "sku": sku,
                "price": p["sales_price"],
                "inventory_management": "shopify",
                "inventory_policy": "continue"
            }],
            "handle": sku.lower().replace(" ","-")
        }
    }
    
    # Extract metafields - OEM numbers and other relevant data
    metafields = []
    
    # Original numbers (OEM) - primary for TecDoc matching
    original_nummer = extract_custom_field(p, "Original_nummer") or extract_custom_field(p, "original_nummer")
    if original_nummer:
        metafields.append({
            "namespace": "custom",
            "key": "original_nummer",
            "value": str(original_nummer),
            "type": "single_line_text_field"
        })
    
    # Produktgruppe (match DB expectations) – use plural collection naming
    if shopify_collection:
        metafields.append({
            "namespace": "custom",
            "key": "Produktgruppe",
            "value": shopify_collection,
            "type": "single_line_text_field"
        })
    
    # Webshop availability flag - extract from custom fields
    i_nettbutikk = extract_custom_field(p, "i_nettbutikk") or "nei"
    metafields.append({
        "namespace": "custom",
        "key": "i_nettbutikk", 
        "value": str(i_nettbutikk),
        "type": "single_line_text_field"
    })
    
    # Additional custom fields for search (exclude inntektskonto)
    custom_field_names = [
        "Spicer Varenummer", "Industries Varenummer", "Tirsan varenummer",
        "ODM varenummer", "IMS varenummer", "Welte varenummer", "Bakkeren varenummer"
    ]
    
    for field_name in custom_field_names:
        val = extract_custom_field(p, field_name)
        if val:
            # Convert field name to safe metafield key
            safe_key = field_name.lower().replace(" ", "_").replace("æ", "ae").replace("ø", "o").replace("å", "a")
            metafields.append({
                "namespace": "custom",
                "key": safe_key,
                "value": str(val),
                "type": "single_line_text_field"
            })
    
    # Add "Number" field for free text search (NOT for TecDoc matching)
    number_field = p.get("number", "")
    if number_field:
        metafields.append({
            "namespace": "custom",
            "key": "number",
            "value": str(number_field),
            "type": "single_line_text_field"
        })
    
    # Legacy fields for backward compatibility
    for field in ["varenummer", "leverandor_nummer"]:
        val = p.get(field, "")
        if val:
            metafields.append({
                "namespace": "custom",
                "key": field,
                "value": str(val),
                "type": "single_line_text_field"
            })
    
    return payload, metafields

def get_all_shopify_ids() -> dict:
    """return {sku:number : product_id} for all Shopify products (250-page loops)"""
    out, page_info = {}, None
    while True:
        url = f"https://{SHOP_DOMAIN}/admin/api/2023-10/products.json?limit=250"
        if page_info:
            url += f"&page_info={page_info}"
        r = requests.get(url, headers=HEAD_SHOP, timeout=30)
        r.raise_for_status()
        
        response_data = r.json()
        if "products" not in response_data:
            print(f"⚠️  No 'products' key in response: {response_data}")
            break
            
        batch = response_data["products"]
        for pr in batch:
            if "variants" in pr and len(pr["variants"]) > 0 and "sku" in pr["variants"][0]:
                sku = pr["variants"][0]["sku"]
                out[sku] = pr["id"]
        
        # pagination link header
        link = r.headers.get("link","")
        if 'rel="next"' in link:
            page_info = link.split("page_info=")[1].split(">")[0]
        else:
            break
    return out

def get_collection_id(collection_name):
    """Get Shopify collection ID by name"""
    try:
        # Try custom collections first, then smart collections
        endpoints = [
            f"https://{SHOP_DOMAIN}/admin/api/2023-10/custom_collections.json",
            f"https://{SHOP_DOMAIN}/admin/api/2023-10/smart_collections.json"
        ]
        
        for endpoint in endpoints:
            response = requests.get(endpoint, headers=HEAD_SHOP, timeout=20)
            if response.status_code == 200:
                data = response.json()
                # Get the collections key (custom_collections or smart_collections)
                collection_key = list(data.keys())[0] if data else None
                if collection_key:
                    collections = data.get(collection_key, [])
                    for collection in collections:
                        if collection.get("title") == collection_name:
                            print(f"✅ Found collection '{collection_name}' with ID: {collection.get('id')}")
                            return collection.get("id")
        
        print(f"⚠️ Collection '{collection_name}' not found in custom or smart collections")
        return None
    except Exception as e:
        print(f"⚠️ Error getting collection {collection_name}: {e}")
        return None

def assign_to_collection(product_id, collection_name):
    """Assign product to Shopify collection"""
    collection_id = get_collection_id(collection_name)
    if not collection_id:
        print(f"⚠️ Collection '{collection_name}' not found")
        return False
    
    try:
        # Add product to collection
        response = requests.post(
            f"https://{SHOP_DOMAIN}/admin/api/2023-10/collects.json",
            headers=HEAD_SHOP,
            json={"collect": {"product_id": product_id, "collection_id": collection_id}},
            timeout=20
        )
        if response.status_code == 201:
            print(f"✅ Added product {product_id} to collection '{collection_name}'")
            return True
        else:
            print(f"⚠️ Failed to add product to collection: {response.status_code}")
            return False
    except Exception as e:
        print(f"⚠️ Error assigning to collection: {e}")
        return False

def sync_to_database(product_data, metafields_data):
    """Sync product data to Railway PostgreSQL database"""
    session = SessionLocal()
    try:
        product_id = str(product_data.get("id"))
        
        # Create or update ShopifyProduct record
        existing_product = session.query(ShopifyProduct).filter(ShopifyProduct.id == product_id).first()
        
        if existing_product:
            # Update existing product
            existing_product.title = product_data.get("title")
            existing_product.handle = product_data.get("handle")
            existing_product.sku = product_data.get("variants", [{}])[0].get("sku")
            existing_product.price = str(product_data.get("variants", [{}])[0].get("price", 0))
            existing_product.inventory_quantity = product_data.get("variants", [{}])[0].get("inventory_quantity", 0)
            existing_product.updated_at = datetime.utcnow()
            print(f"   📝 Updated database product: {product_id}")
        else:
            # Create new product
            new_product = ShopifyProduct(
                id=product_id,
                title=product_data.get("title"),
                handle=product_data.get("handle"),
                sku=product_data.get("variants", [{}])[0].get("sku"),
                price=str(product_data.get("variants", [{}])[0].get("price", 0)),
                inventory_quantity=product_data.get("variants", [{}])[0].get("inventory_quantity", 0),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(new_product)
            print(f"   📝 Created database product: {product_id}")
        
        # Sync metafields to database
        if metafields_data:
            # Remove old metafields for this product
            session.query(ProductMetafield).filter(ProductMetafield.product_id == product_id).delete()
            
            # Add new metafields
            for metafield in metafields_data:
                metafield_record = ProductMetafield(
                    id=f"{product_id}_{metafield.get('key', 'unknown')}",
                    product_id=product_id,
                    namespace=metafield.get("namespace", "custom"),
                    key=metafield.get("key"),
                    value=metafield.get("value"),
                    created_at=datetime.utcnow()
                )
                session.add(metafield_record)
                print(f"   📝 Added metafield: {metafield.get('key')} = {metafield.get('value')}")
        
        session.commit()
        return True
        
    except Exception as e:
        print(f"   ❌ Database sync error: {e}")
        session.rollback()
        return False
    finally:
        session.close()

def create_or_update_product_optimized(payload:dict, metafields:list):
    """Create or update product directly without checking all existing IDs first"""
    sku = payload["product"]["variants"][0]["sku"]
    title = payload["product"]["title"]
    
    try:
        # Prefer update-by-SKU to avoid duplicates
        found = find_variant_by_sku(sku)
        existing_id = found.get("product_id") if found else None
        variant_id = found.get("variant_id") if found else None
        if existing_id:
            update_payload = {"product": {"id": existing_id}}
            # Copy fields except 'handle' to avoid breaking URLs, keep status active
            for k, v in payload["product"].items():
                if k == "handle":
                    continue
                update_payload["product"][k] = v

            update_response = requests.put(
                f"https://{SHOP_DOMAIN}/admin/api/2023-10/products/{existing_id}.json",
                headers=HEAD_SHOP, json=update_payload, timeout=30
            )
            if update_response.status_code == 200:
                updated_product = update_response.json().get("product", {})
                # Ensure variant continues selling at 0 stock
                try:
                    if variant_id:
                        requests.put(
                            f"https://{SHOP_DOMAIN}/admin/api/2023-10/variants/{variant_id}.json",
                            headers=HEAD_SHOP,
                            json={"variant": {"id": variant_id, "inventory_management": "shopify", "inventory_policy": "continue"}},
                            timeout=20,
                        )
                except Exception as e:
                    print(f"   ⚠️ Variant policy update exception: {e}")
                # Update metafields
                if metafields:
                    for metafield in metafields:
                        metafield_payload = {
                            "metafield": {
                                **metafield,
                                "owner_id": existing_id,
                                "owner_resource": "product"
                            }
                        }
                        try:
                            requests.post(
                                f"https://{SHOP_DOMAIN}/admin/api/2023-10/metafields.json",
                                headers=HEAD_SHOP, json=metafield_payload, timeout=20
                            )
                        except Exception as e:
                            print(f"   ⚠️ Metafield update exception: {e}")
                # Sync to DB using update response (no extra GET)
                sync_to_database(updated_product, metafields)
                return existing_id
            else:
                print(f"   ❌ Update-by-SKU failed ({update_response.status_code}), falling back to create…")

        # Try to create product first (most common case for new sync)
        response = requests.post(
            f"https://{SHOP_DOMAIN}/admin/api/2023-10/products.json",
            headers=HEAD_SHOP, json=payload, timeout=30
        )
        
        if response.status_code == 201:
            # Product created successfully
            product_data = response.json()
            product = product_data.get("product", {})
            product_id = product.get("id")
            
            # Add metafields to Shopify
            if metafields and product_id:
                for metafield in metafields:
                    metafield_payload = {
                        "metafield": {
                            **metafield,
                            "owner_id": product_id,
                            "owner_resource": "product"
                        }
                    }
                    
                    try:
                        meta_response = requests.post(
                            f"https://{SHOP_DOMAIN}/admin/api/2023-10/metafields.json",
                            headers=HEAD_SHOP, json=metafield_payload, timeout=20
                        )
                        if meta_response.status_code != 201:
                            print(f"   ⚠️ Metafield failed for {metafield.get('key', 'N/A')}: {meta_response.status_code}")
                    except Exception as e:
                        print(f"   ⚠️ Metafield exception: {e}")
            
            # 🚨 CRITICAL: Sync to database as well!
            sync_to_database(product, metafields)
            
            return product_id
            
        elif response.status_code == 422:
            # Creation failed, try update-by-SKU as fallback
            found = find_variant_by_sku(sku)
            existing_id = found.get("product_id") if found else None
            variant_id = found.get("variant_id") if found else None
            if existing_id:
                update_payload = {"product": {"id": existing_id}}
                for k, v in payload["product"].items():
                    if k == "handle":
                        continue
                    update_payload["product"][k] = v
                update_response = requests.put(
                    f"https://{SHOP_DOMAIN}/admin/api/2023-10/products/{existing_id}.json",
                    headers=HEAD_SHOP, json=update_payload, timeout=30
                )
                if update_response.status_code == 200:
                    updated_product = update_response.json().get("product", {})
                    # Ensure variant continues selling at 0 stock
                    try:
                        if variant_id:
                            requests.put(
                                f"https://{SHOP_DOMAIN}/admin/api/2023-10/variants/{variant_id}.json",
                                headers=HEAD_SHOP,
                                json={"variant": {"id": variant_id, "inventory_management": "shopify", "inventory_policy": "continue"}},
                                timeout=20,
                            )
                    except Exception as e:
                        print(f"   ⚠️ Variant policy update exception: {e}")
                    if metafields:
                        for metafield in metafields:
                            metafield_payload = {
                                "metafield": {
                                    **metafield,
                                    "owner_id": existing_id,
                                    "owner_resource": "product"
                                }
                            }
                            try:
                                requests.post(
                                    f"https://{SHOP_DOMAIN}/admin/api/2023-10/metafields.json",
                                    headers=HEAD_SHOP, json=metafield_payload, timeout=20
                                )
                            except Exception as e:
                                print(f"   ⚠️ Metafield update exception: {e}")
                    sync_to_database(updated_product, metafields)
                    return existing_id
            else:
                print(f"   ❌ Creation failed: {response.status_code} - {response.text[:160]}")
                return None
        else:
            print(f"   ❌ Unexpected error: {response.status_code} - {response.text[:200]}")
            return None
            
    except Exception as e:
        print(f"   ❌ Exception creating/updating product: {e}")
        return None

def ensure_product(shop_ids:dict, payload:dict, metafields:list):
    """Legacy function - now calls optimized version"""
    return create_or_update_product_optimized(payload, metafields)

# ---------- Flask API ----------
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for Railway deployment"""
    return jsonify({"status": "healthy", "service": "sync-service"})

@app.get("/test/ma18002")
def test_ma18002():
    """Diagnostic endpoint: fetch MA18002 from Rackbeat and evaluate filters"""
    try:
        # Query Rackbeat directly for MA18002
        params = {
            "search": "MA18002",
            "fields": "number,name,sales_price,available_quantity,group,metadata",
            "limit": 50,
            "page": 1,
        }
        r = requests.get(RACKBEAT_API, headers=HEAD_RACK, params=params, timeout=30)
        if r.status_code not in [200, 206]:
            return jsonify({"error": f"Rackbeat API error", "status": r.status_code}), 502

        js = r.json()
        # Support both shapes: {products: [...]} or {data: [...]} just in case
        items = js.get("products") or js.get("data") or []

        product = None
        for p in items:
            if p.get("number") == "MA18002":
                product = p
                break

        if not product:
            return jsonify({
                "found": False,
                "candidates": [p.get("number") for p in items[:10]],
                "count": len(items)
            })

        # Extract diagnostics
        group_name = product.get("group", {}).get("name", "")
        stock = product.get("available_quantity", 0)
        price = product.get("sales_price", 0)
        i_nb = get_i_nettbutikk_from_metadata(product.get("metadata", []))
        should_sync = filter_keep(product)

        meta_list = [
            {"slug": m.get("slug"), "value": m.get("value")} for m in product.get("metadata", [])
        ]

        return jsonify({
            "found": True,
            "number": product.get("number"),
            "name": product.get("name"),
            "group": group_name,
            "stock": stock,
            "price": price,
            "i_nettbutikk": i_nb,
            "should_sync": should_sync,
            "filter_checks": {
                "group_ok": group_name in ["Drivaksel", "Mellomaksel"],
                "stock_ok": stock >= 1,
                "price_ok": price > 0,
                "i_nettbutikk_ok": i_nb == "ja",
            },
            "metadata": meta_list,
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.post("/sync/full")
def sync_full():
    try:
        print("🔄 Starting optimized sync with database sync...")
        started_at = time.time()
        aborted_by_timeout = False
        
        # Initialize database
        init_db()
        
        rack_all   = fetch_all_rackbeat()
        filtered   = [p for p in rack_all if filter_keep(p)]
        print(f"✅  Rackbeat total {len(rack_all)} → holder {len(filtered)}")

        if not filtered:
            print("⚠️  No products to sync after filtering")
            return jsonify({
                "rackbeat_total": len(rack_all),
                "filtered_kept": 0,
                "shopify_synced": 0,
                "message": "No products met filtering criteria"
            })

        print("🔄 Processing products directly (optimized)...")
        success_count = 0
        kept_skus = set()
        
        for i, p in enumerate(filtered):
            # Hard timeout guard
            if time.time() - started_at > SYNC_HARD_TIMEOUT_SECONDS:
                print("⏱️  Hard timeout reached — aborting further processing")
                aborted_by_timeout = True
                break
            try:
                print(f"📦 Processing {i+1}/{len(filtered)}: {p.get('number', 'N/A')} - {p.get('name', 'N/A')[:40]}")
                payload, mfs = map_to_shop_payload(p)
                
                # Use optimized create/update function
                pid = create_or_update_product_optimized(payload, mfs)
                
                if pid is not None:
                    success_count += 1
                    sku = payload["product"]["variants"][0]["sku"]
                    kept_skus.add(sku)
                    
                    # Assign to collection
                    product_type = payload["product"].get("product_type", "")
                    if product_type in ["Drivaksler", "Mellomaksler"]:
                        try:
                            assign_result = assign_to_collection(pid, product_type)
                            if assign_result:
                                print(f"   ✅ Assigned to {product_type} collection")
                            else:
                                print(f"   ⚠️ Collection assignment failed for {product_type}")
                        except Exception as e:
                            print(f"   ⚠️ Collection assignment error: {e}")
                    
                    print(f"   ✅ Product synced successfully (ID: {pid})")
                else:
                    print(f"   ❌ Product sync failed")
                
                # Small delay to avoid rate limits
                if i % 10 == 0 and i > 0:
                    print(f"   💤 Brief pause after {i} products...")
                    time.sleep(2)
                    
            except Exception as e:
                print(f"⚠️  Error processing product {p.get('number', 'N/A')}: {e}")
                import traceback
                traceback.print_exc()
                continue

        print("✅ Optimized sync with database sync completed!")
        print(f"   Products processed: {len(filtered)}")
        print(f"   Successful syncs: {success_count}")
        print(f"   Success rate: {success_count/len(filtered)*100:.1f}%")
        
        # Unpublish products in our categories that were NOT kept this run
        try:
            print("🔧 Cleaning up non-kept products (draft)...")
            unpublish_nonkept_products(kept_skus)
        except Exception as e:
            print(f"   ⚠️ Cleanup step failed: {e}")
        
        # Verify database sync
        session = SessionLocal()
        try:
            db_count = session.query(ShopifyProduct).count()
            metafield_count = session.query(ProductMetafield).count()
            print(f"   Database products: {db_count}")
            print(f"   Database metafields: {metafield_count}")
        finally:
            session.close()
        
        return jsonify({
            "rackbeat_total": len(rack_all),
            "filtered_kept":  len(filtered),
            "shopify_synced": success_count,
            "success_rate": f"{success_count/len(filtered)*100:.1f}%" if filtered else "0.0%",
            "message": "Optimized sync completed successfully" if not aborted_by_timeout else "Partial sync stopped by hard timeout",
            "aborted_by_timeout": aborted_by_timeout
        })
        
    except Exception as e:
        print(f"❌ Sync error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.post("/sync/legacy")
def sync_full_legacy():
    """Legacy sync method using get_all_shopify_ids (kept for backup)"""
    try:
        print("🔄 Starting legacy sync...")
        rack_all   = fetch_all_rackbeat()
        filtered   = [p for p in rack_all if filter_keep(p)]
        print(f"✅  Rackbeat total {len(rack_all)} → holder {len(filtered)}")

        print("🔄 Getting Shopify product IDs (legacy method)...")
        shop_ids   = get_all_shopify_ids()
        kept_skus  = set()

        print("🔄 Processing products...")
        for i, p in enumerate(filtered):
            try:
                print(f"📦 Processing {i+1}/{len(filtered)}: {p.get('number', 'N/A')}")
                payload, mfs = map_to_shop_payload(p)
                pid = ensure_product(shop_ids, payload, mfs)
                if pid is not None:
                    kept_skus.add(payload["product"]["variants"][0]["sku"])
            except Exception as e:
                print(f"⚠️  Error processing product {p.get('number', 'N/A')}: {e}")
                continue

        print("🔄 Setting invalid products to draft...")
        # draft products no longer valid
        for sku,pid in shop_ids.items():
            if sku not in kept_skus:
                try:
                    requests.put(
                        f"https://{SHOP_DOMAIN}/admin/api/2023-10/products/{pid}.json",
                        headers=HEAD_SHOP,
                        json={"product":{"id":pid,"status":"draft"}}
                    )
                except Exception as e:
                    print(f"⚠️  Error setting {sku} to draft: {e}")

        print("✅ Legacy sync completed!")
        return jsonify({
            "rackbeat_total": len(rack_all),
            "filtered_kept":  len(filtered),
            "shopify_active": len(kept_skus)
        })
    except Exception as e:
        print(f"❌ Legacy sync error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(port=int(os.getenv("PORT_SYNC",8001)), host="0.0.0.0") 