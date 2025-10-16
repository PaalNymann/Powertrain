#!/usr/bin/env python3
"""
Scrape registration numbers from finn.no using their search API
"""
import requests
import time
import re
import json

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json"
}

def get_finn_ads(search_query, limit=50):
    """Get finn.no ad IDs from search"""
    ads = []
    page = 1
    
    # Use finn.no's search API endpoint
    base_url = "https://www.finn.no/api/search-qf"
    
    while len(ads) < limit and page <= 10:
        params = {
            "searchkey": "SEARCH_ID_CAR_USED",
            "vertical": "car",
            "q": search_query,
            "page": page
        }
        
        try:
            r = requests.get(base_url, params=params, headers=HEADERS, timeout=10)
            if r.status_code == 200:
                data = r.json()
                docs = data.get("docs", [])
                
                if not docs:
                    break
                
                for doc in docs:
                    if len(ads) >= limit:
                        break
                    ad_id = doc.get("ad_id") or doc.get("id")
                    if ad_id:
                        ads.append(ad_id)
                
                print(f"  Side {page}: Fant {len(docs)} annonser (totalt {len(ads)})")
                page += 1
                time.sleep(0.5)
            else:
                print(f"  Feil ved søk: {r.status_code}")
                break
        except Exception as e:
            print(f"  Exception: {e}")
            break
    
    return ads

def get_registration_from_ad(ad_id):
    """Extract registration number from finn.no ad"""
    try:
        # Try to get ad details
        url = f"https://www.finn.no/api/car-ad/{ad_id}"
        r = requests.get(url, headers=HEADERS, timeout=10)
        
        if r.status_code == 200:
            data = r.json()
            
            # Look for registration number in various fields
            reg_nr = None
            
            # Check common fields
            if "registration_number" in data:
                reg_nr = data["registration_number"]
            elif "regnr" in data:
                reg_nr = data["regnr"]
            elif "properties" in data:
                props = data["properties"]
                for prop in props:
                    if isinstance(prop, dict):
                        if prop.get("name") == "Registreringsnummer":
                            reg_nr = prop.get("value")
                            break
            
            # Clean up registration number
            if reg_nr:
                reg_nr = re.sub(r'\s+', '', reg_nr).upper()
                if re.match(r'^[A-Z]{2}\d{5}$', reg_nr):
                    return reg_nr
        
        # Fallback: scrape HTML page
        url = f"https://www.finn.no/car/used/ad.html?finnkode={ad_id}"
        r = requests.get(url, headers=HEADERS, timeout=10)
        
        if r.status_code == 200:
            # Look for registration number pattern in HTML
            matches = re.findall(r'\b([A-Z]{2}\s?\d{5})\b', r.text)
            for match in matches:
                clean = match.replace(' ', '')
                if re.match(r'^[A-Z]{2}\d{5}$', clean):
                    return clean
        
    except Exception as e:
        pass
    
    return None

def get_reg_numbers(search_query, limit=50):
    """Get registration numbers from finn.no search"""
    print(f"Søker etter: {search_query}")
    
    # Get ad IDs
    ad_ids = get_finn_ads(search_query, limit=limit*3)  # Get more ads than needed
    print(f"Fant {len(ad_ids)} annonser, henter registreringsnumre...")
    
    reg_numbers = set()
    
    for idx, ad_id in enumerate(ad_ids, 1):
        if len(reg_numbers) >= limit:
            break
        
        reg_nr = get_registration_from_ad(ad_id)
        if reg_nr:
            reg_numbers.add(reg_nr)
            print(f"  [{len(reg_numbers)}/{limit}] {reg_nr}")
        
        time.sleep(0.3)  # Be nice to finn.no
    
    return list(reg_numbers)

if __name__ == "__main__":
    all_regs = []
    
    print("\n" + "="*60)
    print("HENTER 20 VOLVO V70 REGISTRERINGSNUMRE")
    print("="*60)
    v70_regs = get_reg_numbers("Volvo V70", limit=20)
    all_regs.extend([(reg, "Volvo V70") for reg in v70_regs])
    
    print("\n" + "="*60)
    print("HENTER 30 ANDRE VOLVO REGISTRERINGSNUMRE")
    print("="*60)
    other_regs = get_reg_numbers("Volvo -V70", limit=30)
    all_regs.extend([(reg, "Volvo (andre)") for reg in other_regs if reg not in v70_regs])
    
    print("\n" + "="*60)
    print(f"RESULTAT: {len(all_regs)} REGISTRERINGSNUMRE")
    print("="*60)
    
    for reg, model in all_regs:
        print(f"{reg} ({model})")
    
    # Save to file
    with open("volvo_registration_numbers.txt", "w") as f:
        for reg, model in all_regs:
            f.write(f"{reg}\n")
    
    print(f"\n✅ Lagret {len(all_regs)} registreringsnumre til volvo_registration_numbers.txt")
