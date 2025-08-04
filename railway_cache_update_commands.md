# Railway Cache Update Commands

## After Railway Deployment (with pagination fix)

Replace `YOUR_RAILWAY_URL` with your actual Railway URL (e.g., `https://your-app.railway.app`)

### 1. Health Check
```bash
curl "YOUR_RAILWAY_URL/health"
```

### 2. Check Current Cache Stats
```bash
curl "YOUR_RAILWAY_URL/api/cache/stats"
```

### 3. Update Cache (This will fetch ALL products with new pagination fix)
```bash
curl -X POST "YOUR_RAILWAY_URL/api/cache/update"
```

### 4. Verify Updated Cache Stats
```bash
curl "YOUR_RAILWAY_URL/api/cache/stats"
```

### 5. Test OEM Search
```bash
curl "YOUR_RAILWAY_URL/api/part_number_search?part_number=TEST123"
```

## Expected Results

### Before (old pagination):
- Products: ~250 (only first page)
- Metafields: ~250

### After (new pagination fix):
- Products: All products in Shopify (could be thousands)
- Metafields: All metafields for all products

## Notes

- The cache update may take several minutes for large product catalogs
- The new pagination fix will fetch ALL products, not just the first 250
- Database will now contain complete product catalog with metafields
- Railway automatically deploys changes when you push to Git

## Python Script Alternative

You can also use the Python script:
```bash
python test_railway_cache_update.py YOUR_RAILWAY_URL
``` 