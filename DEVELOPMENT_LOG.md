# Powertrain System Development Log

## Current Status (Last Updated: Before Mac Restart)

### Project Overview
- **Main Service**: License Plate Service (app.py - Port 8000)
- **Sync Service**: Rackbeat to Shopify sync (sync_service.py - Port 8001)
- **Database**: PostgreSQL with SQLite fallback for Shopify product caching
- **Current Focus**: Database testing and optimization

### Database Architecture
```
ShopifyProduct (products cache)
├── ProductMetafield (metafields storage)
└── OemIndex (fast OEM search index)
```

### Key Functions Being Tested
1. `search_products_by_oem()` - Fast database search by OEM number
2. `update_shopify_cache()` - Sync Shopify products to database
3. `get_cache_stats()` - Database statistics
4. Complete workflow: License plate → Vehicle → Parts search

### Test Files Available
- `test_database_simple.py` - Basic functionality test
- `test_cache_update.py` - Cache update testing  
- `test_database.py` - Comprehensive database testing
- `test_complete_flow.py` - End-to-end workflow test

### Environment Variables Needed
```bash
# Database
DATABASE_URL=postgresql://username:password@host:port/database

# APIs
SVV_API_KEY=your_svv_api_key_here
RACKBEAT_API_KEY=your_rackbeat_token_here
SHOPIFY_DOMAIN=bm0did-zc.myshopify.com
SHOPIFY_TOKEN=your_shopify_token_here

# Flask
PORT_APP=8000
PORT_SYNC=8001
```

### Current Database File
- `powertrain.db` (36KB) - SQLite database with cached data

### Next Steps After Restart
1. **Activate virtual environment**: `source venv/bin/activate`
2. **Check database status**: `curl http://127.0.0.1:8000/api/cache/stats`
3. **Run database test**: `python test_database_simple.py`
4. **Test cache update**: `python test_cache_update.py`

### API Endpoints to Test
- `GET /health` - Health check
- `GET /api/cache/stats` - Database statistics
- `POST /api/cache/update` - Update Shopify cache
- `GET /api/oem_search?oem=TEST123` - Fast OEM search
- `GET /api/car_parts_search?regnr=KH66644` - Complete workflow

### Recent Testing Focus
- Database connectivity and initialization
- Shopify product cache synchronization
- Fast OEM number search optimization
- Complete workflow integration testing

### Known Issues/Notes
- Database uses PostgreSQL in production, SQLite locally
- Cache update can take several minutes for large product catalogs
- OEM search extracts patterns: 6-15 character alphanumeric codes
- System designed for Railway deployment with automatic DATABASE_URL

### Quick Start Commands
```bash
# Start main service
python app.py

# Start sync service (in another terminal)
python sync_service.py

# Test database functionality
python test_database_simple.py

# Update cache from Shopify
curl -X POST http://127.0.0.1:8000/api/cache/update
```

---
*This log was created before Mac restart to preserve development context* 