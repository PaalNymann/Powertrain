#!/usr/bin/env python3
"""
Warm the TecDoc OEM cache for car shafts only.
- Product groups: 100062 (Drive Shaft), 100703 (Propshaft, axle drive)
- For each article, fetch OEMs via POST /articles/details and store in tecdoc_article_oems
- Skips articles already in cache unless --force is provided

Environment:
- DATABASE_URL (Railway PostgreSQL URL)
- Optional: MAX_PAGES, PER_PAGE via CLI args

Usage examples:
  python warm_tecdoc_cache.py
  python warm_tecdoc_cache.py --groups 100062,100703 --max-pages 50 --per-page 100 --sleep 0.2
"""
import os
import time
import json
import argparse
import requests
from dotenv import load_dotenv
from typing import List, Tuple

# Reuse API config from the runtime module
from rapidapi_tecdoc import (
    CATALOG_BASE_URL,
    CATALOG_HEADERS,
    LANG_ID,
    COUNTRY_ID,
)
from database import init_db, get_cached_oems_for_article, upsert_article_oems

load_dotenv()

DEFAULT_GROUPS: List[Tuple[int, str]] = [(100062, "Drivaksler"), (100703, "Mellomaksler")]


def list_articles_by_group(group_id: int, page: int, per_page: int):
    url = f"{CATALOG_BASE_URL}/articles-by-product-group/list"
    params = {
        'productGroupId': group_id,
        'langId': LANG_ID,
        'countryId': COUNTRY_ID,
        'page': page,
        'perPage': per_page,
    }
    r = requests.get(url, headers=CATALOG_HEADERS, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def fetch_article_oems(article_id: int) -> List[str]:
    url = f"{CATALOG_BASE_URL}/articles/details"
    payload = f"langId={LANG_ID}&countryId={COUNTRY_ID}&articleId={article_id}"
    headers = {**CATALOG_HEADERS, 'content-type': 'application/x-www-form-urlencoded'}
    r = requests.post(url, headers=headers, data=payload, timeout=15)
    if r.status_code != 200:
        return []
    data = r.json()
    oems: List[str] = []
    if isinstance(data, dict):
        if isinstance(data.get('articleOemNo'), list):
            for it in data['articleOemNo']:
                if isinstance(it, dict):
                    v = it.get('oemDisplayNo') or it.get('oemNumber') or it.get('oeNumber') or it.get('articleOemNo')
                    if v:
                        oems.append(str(v).strip())
        for alt in ('oemNumbers', 'oeNumbers'):
            arr = data.get(alt)
            if isinstance(arr, list):
                for it in arr:
                    if isinstance(it, dict):
                        v = it.get('oemDisplayNo') or it.get('oemNumber') or it.get('oeNumber') or it.get('articleOemNo')
                    else:
                        v = str(it)
                    if v:
                        oems.append(str(v).strip())
    # Deduplicate
    return sorted({x for x in oems if x})


def warm_group(group_id: int, group_name: str, max_pages: int, per_page: int, sleep_s: float, force: bool):
    print(f"\n🚀 Warming cache for {group_name} (ID {group_id})")
    page = 1
    total_cached = 0
    total_skipped = 0
    total_errors = 0
    while page <= max_pages:
        try:
            data = list_articles_by_group(group_id, page, per_page)
        except Exception as e:
            print(f"   ❌ list page {page} failed: {e}")
            total_errors += 1
            break
        articles = (data or {}).get('articles') or []
        if not articles:
            break
        print(f"   📄 Page {page}: {len(articles)} articles")
        for a in articles:
            aid = a.get('articleId')
            if not aid:
                continue
            if not force:
                cached = get_cached_oems_for_article(str(aid))
                if cached:
                    total_skipped += 1
                    continue
            oems = fetch_article_oems(aid)
            if not oems:
                continue
            try:
                upsert_article_oems(
                    article_id=str(aid),
                    product_group_id=group_id,
                    supplier_id=a.get('supplierId') or 0,
                    supplier_name=a.get('supplierName') or '',
                    article_product_name=a.get('articleProductName') or '',
                    oem_numbers=oems,
                )
                total_cached += 1
            except Exception as ex:
                print(f"   ⚠️ upsert failed for {aid}: {ex}")
                total_errors += 1
            time.sleep(sleep_s)
        # hasMore may indicate continuation
        has_more = (data or {}).get('hasMore')
        page += 1
        if not has_more:
            break
    print(f"   ✅ Done {group_name}: cached {total_cached}, skipped {total_skipped}, errors {total_errors}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--groups', default='100062,100703', help='Comma-separated productGroupIds')
    parser.add_argument('--max-pages', type=int, default=1000)
    parser.add_argument('--per-page', type=int, default=100)
    parser.add_argument('--sleep', type=float, default=0.2)
    parser.add_argument('--force', action='store_true')
    args = parser.parse_args()

    init_db()

    groups = []
    for gid in args.groups.split(','):
        gid = gid.strip()
        if not gid:
            continue
        try:
            groups.append((int(gid), ''))
        except ValueError:
            continue
    # Map names where known
    named = {100062: 'Drivaksler', 100703: 'Mellomaksler'}
    groups = [(gid, named.get(gid, f'Group {gid}')) for gid, _ in groups]

    print(f"Starting warm-up for groups: {[g for g,_ in groups]} | max_pages={args.max_pages} per_page={args.per_page}")
    for gid, gname in groups:
        warm_group(gid, gname, args.max_pages, args.per_page, args.sleep, args.force)
    print("\n🎉 Cache warm-up complete.")


if __name__ == '__main__':
    main()
