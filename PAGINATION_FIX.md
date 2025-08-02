# Pagination Fix for Shopify API Integration

## Problem
Systemet hentet kun maksimalt 250 produkter inn i databasen på grunn av feil paginering i `app.py`. Dette skjedde fordi koden brukte `page` parameter for paginering, men Shopify API bruker ikke denne parameteren.

## Root Cause
I `app.py` linje 350-351 ble følgende kode brukt:
```python
# Pagination - use page parameter instead of Link headers
page += 1
shopify_url = f"https://{SHOPIFY_DOMAIN}/admin/api/{SHOPIFY_VERSION}/products.json?limit=250&page={page}"
```

Shopify API støtter ikke `page` parameter. I stedet bruker den Link headers med `page_info` parameter for paginering.

## Solution
Endret paginering-logikken i `app.py` til å bruke korrekt Shopify API paginering:

### Før (feil):
```python
# Fetch products with pagination
page = 1
while True:
    res = requests.get(shopify_url, headers=headers, timeout=30)
    # ... process products ...
    
    # Pagination - use page parameter instead of Link headers
    page += 1
    shopify_url = f"https://{SHOPIFY_DOMAIN}/admin/api/{SHOPIFY_VERSION}/products.json?limit=250&page={page}"
```

### Etter (korrekt):
```python
# Fetch products with pagination using Link headers
page_info = None
page_count = 0
while True:
    page_count += 1
    current_url = shopify_url
    if page_info:
        current_url += f"&page_info={page_info}"
    
    res = requests.get(current_url, headers=headers, timeout=30)
    # ... process products ...
    
    # Check for pagination using Link headers
    link = res.headers.get("link", "")
    if 'rel="next"' in link:
        page_info = link.split("page_info=")[1].split(">")[0]
    else:
        print(f"✅ No more pages available")
        break
```

## Key Changes
1. **Bruker `page_info` fra Link headers** i stedet for `page` parameter
2. **Sjekker for `rel="next"`** i Link headers for å finne neste side
3. **Øker sikkerhetsgrensen** fra 50 til 100 sider (25,000 produkter i stedet for 12,500)
4. **Forbedret logging** for bedre debugging

## Verification
Testet endringen med `test_pagination_fix.py` som simulerer:
- 3 sider med produkter (250 + 250 + 100 = 600 totalt)
- Korrekt håndtering av Link headers
- Stopp når ingen flere sider er tilgjengelige

## Impact
- **Før**: Kun 250 produkter hentet inn i databasen
- **Etter**: Alle produkter hentet inn (opptil 25,000 med sikkerhetsgrensen)

## Files Modified
- `app.py`: Endret `update_cache()` funksjonen for korrekt paginering

## Files Unchanged
- `sync_service.py`: Brukte allerede korrekt paginering
- `cleanup_shopify.py`: Brukte allerede korrekt paginering
- Andre filer: Brukte allerede korrekt paginering

## Testing
Kjør testen for å verifisere endringen:
```bash
source venv/bin/activate
python test_pagination_fix.py
```

## Deployment
Endringen er klar for deployment. Ingen ytterligere konfigurasjon kreves. 