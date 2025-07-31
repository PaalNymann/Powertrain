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

# ---------- ENV ----------
RACKBEAT_API   = os.getenv("RACKBEAT_ENDPOINT", "https://app.rackbeat.com/api/products")
RACKBEAT_KEY   = os.getenv("RACKBEAT_API_KEY")
SHOP_DOMAIN    = os.getenv("SHOPIFY_DOMAIN")
SHOP_TOKEN     = os.getenv("SHOPIFY_TOKEN")

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

def rb_page(page:int=1, limit:int=250):
    """Return (products, pages) tuple for given Rackbeat page"""
    url = f"{RACKBEAT_API}?page={page}&limit={limit}"
    r = requests.get(url, headers=HEAD_RACK, timeout=30)
    if r.status_code not in [200, 206]:  # Accept both 200 and 206 (Partial Content)
        raise RuntimeError(f"Rackbeat page {page} → {r.status_code}")
    js = r.json()
    return js["products"], js["pages"]

def fetch_all_rackbeat() -> list[dict]:
    """Download every Rackbeat product page-by-page"""
    all_prod, page, pages = [], 1, 1
    while page <= pages:
        prods, pages = rb_page(page)
        print(f"📥  Page {page}/{pages} → {len(prods)} items")
        all_prod.extend(prods)
        page += 1
    return all_prod

def filter_keep(p:dict) -> bool:
    return p.get("available_quantity",0) > 0 and p.get("sales_price",0) > 0



def map_to_shop_payload(p:dict) -> tuple[dict,dict]:
    """Return (product_payload, metafield_payload_list)"""
    sku = p["number"]
    payload = {
        "product": {
            "title": p["name"] or sku,
            "status": "active",
            "variants":[{"sku": sku, "price": p["sales_price"]}],
            "handle": sku.lower().replace(" ","-")
        }
    }
    
    # --- metafields (OEM fields for TecDoc matching + number for free text search)
    # For now, we'll create empty metafields that can be updated later
    fields = {
        "number":                p.get("number", ""),  # For free text search (unique customer number)
        "original_nummer":       "N/A",  # For TecDoc matching - will be updated later
        "tirsan_varenummer":     "N/A",  # For TecDoc matching - will be updated later
        "odm_varenummer":        "N/A",  # For TecDoc matching - will be updated later
        "ims_varenummer":        "N/A",  # For TecDoc matching - will be updated later
        "welte_varenummer":      "N/A",  # For TecDoc matching - will be updated later
        "bakkeren_varenummer":   "N/A",  # For TecDoc matching - will be updated later
    }
    metafields = [
        {
            "namespace":"custom",
            "key":k,
            "type":"single_line_text_field",
            "value":v or ""
        } for k,v in fields.items()
    ]
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

def ensure_product(shop_ids:dict, payload:dict, metafields:list):
    sku = payload["product"]["variants"][0]["sku"]
    if sku in shop_ids:
        pid = shop_ids[sku]
        # update price (variant 0)
        response = requests.get(
            f"https://{SHOP_DOMAIN}/admin/api/2023-10/products/{pid}.json",
            headers=HEAD_SHOP, timeout=20
        )
        
        if response.status_code != 200:
            print(f"⚠️  Failed to get product {sku}: {response.status_code}")
            return None
            
        vid = response.json()["product"]["variants"][0]["id"]
        requests.put(
            f"https://{SHOP_DOMAIN}/admin/api/2023-10/variants/{vid}.json",
            headers=HEAD_SHOP, json={"variant":{"price":payload["product"]["variants"][0]["price"]}}
        )
        # update metafields
        for mf in metafields:
            mf["owner_id"] = pid
            mf["owner_resource"] = "product"
            requests.post(
                f"https://{SHOP_DOMAIN}/admin/api/2023-10/metafields.json",
                headers=HEAD_SHOP, json={"metafield":mf}
            )
    else:
        # create new product
        response = requests.post(
            f"https://{SHOP_DOMAIN}/admin/api/2023-10/products.json",
            headers=HEAD_SHOP, json=payload
        )
        
        if response.status_code != 201:
            print(f"⚠️  Failed to create product {sku}: {response.status_code} - {response.text}")
            return None
            
        pr = response.json()["product"]
        pid = pr["id"]
        for mf in metafields:
            mf.update({"owner_id":pid,"owner_resource":"product"})
            requests.post(
                f"https://{SHOP_DOMAIN}/admin/api/2023-10/metafields.json",
                headers=HEAD_SHOP, json={"metafield":mf}
            )
    return pid

# ---------- Flask API ----------
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for Railway deployment"""
    return jsonify({"status": "healthy", "service": "sync-service"})

@app.post("/sync/full")
def sync_full():
    try:
        print("🔄 Starting sync...")
        rack_all   = fetch_all_rackbeat()
        filtered   = [p for p in rack_all if filter_keep(p)]
        print(f"✅  Rackbeat total {len(rack_all)} → holder {len(filtered)}")

        print("🔄 Getting Shopify product IDs...")
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

        print("✅ Sync completed!")
        return jsonify({
            "rackbeat_total": len(rack_all),
            "filtered_kept":  len(filtered),
            "shopify_active": len(kept_skus)
        })
    except Exception as e:
        print(f"❌ Sync error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(port=int(os.getenv("PORT_SYNC",8001)), host="0.0.0.0") 