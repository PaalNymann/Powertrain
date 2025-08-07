# Railway Debugging Guide

## MecaParts API Issues on Railway

### Problem Description
The MecaParts API works locally but fails on Railway deployment. This is typically caused by environment variable configuration issues or network connectivity problems.

### Step-by-Step Debugging

#### 1. Check Environment Variables
First, verify all environment variables are set correctly in Railway:

```bash
# Check Railway environment variables
railway variables list
```

Required variables for MecaParts API:
- `SHOPIFY_DOMAIN`
- `SHOPIFY_TOKEN` 
- `MECAPARTS_ENDPOINT`
- `SHOPIFY_VERSION`

#### 2. Test Environment Validation
The app now includes environment validation. Check Railway logs for:
```
✅ Environment validation passed
🔧 SHOPIFY_DOMAIN: your-store.myshopify.com
🔧 MECAPARTS_ENDPOINT: https://your-store.myshopify.com/admin/api/2023-10/apps/mecaparts/api/vehicle_parts
```

If you see validation errors, fix the missing environment variables.

#### 3. Test MecaParts API Directly
Use the new test endpoint to isolate MecaParts issues:

```bash
curl "https://your-railway-url.railway.app/api/test_mecaparts"
```

Expected response:
```json
{
  "success": true,
  "test_data": {
    "brand": "VOLVO",
    "model": "XC90", 
    "year": "2015"
  },
  "oem_numbers": [...],
  "count": 5,
  "endpoint": "https://your-store.myshopify.com/admin/api/2023-10/apps/mecaparts/api/vehicle_parts"
}
```

#### 4. Check Railway Logs
Look for these specific error patterns in Railway logs:

**Timeout Errors:**
```
❌ MecaParts API timeout after 30 seconds
```

**Connection Errors:**
```
❌ MecaParts API connection error: [Errno 110] Connection timed out
```

**Authentication Errors:**
```
❌ MecaParts API error: 401
❌ Response text: {"errors":"Unauthorized"}
```

**404 Errors:**
```
❌ MecaParts API error: 404
❌ Response text: {"errors":"Not Found"}
```

#### 5. Common Fixes

**Fix 1: Correct MecaParts Endpoint**
Ensure `MECAPARTS_ENDPOINT` includes the full admin API path:
```
✅ CORRECT: https://your-store.myshopify.com/admin/api/2023-10/apps/mecaparts/api/vehicle_parts
❌ WRONG: https://your-store.myshopify.com/apps/mecaparts/api/vehicle_parts
```

**Fix 2: Verify Shopify Token**
- Ensure `SHOPIFY_TOKEN` starts with `shpat_`
- Verify the token has admin API access
- Check if the token has access to the MecaParts app

**Fix 3: Check App Installation**
- Verify MecaParts app is installed in your Shopify store
- Check if the app is active and accessible

**Fix 4: Network Issues**
- Railway may have different network restrictions than local development
- Check if Railway can reach Shopify's servers
- Verify no firewall rules are blocking the connection

#### 6. Advanced Debugging

**Enable Detailed Logging**
The app now includes detailed logging for MecaParts API calls. Look for:
```
🔍 Calling MecaParts API: https://your-store.myshopify.com/admin/api/2023-10/apps/mecaparts/api/vehicle_parts
📋 Payload: {'brand': 'VOLVO', 'model': 'XC90', 'year': '2015'}
🔑 Headers: {'X-Shopify-Access-Token': 'shpat_...', 'Content-Type': 'application/json'}
📡 Response status: 200
📡 Response headers: {...}
📦 Response data: {...}
```

**Test with Different Vehicles**
Try different vehicle combinations to see if the issue is specific to certain data:
```bash
# Test with different license plates
curl "https://your-railway-url.railway.app/api/car_parts_search?regnr=KH66644"
curl "https://your-railway-url.railway.app/api/car_parts_search?regnr=AB12345"
```

#### 7. Fallback Strategy

If MecaParts API continues to fail on Railway, consider:

1. **Use Local MecaParts Service**: Run MecaParts API locally and expose it via ngrok
2. **Direct TecDoc Integration**: Integrate directly with TecDoc API instead of through MecaParts
3. **Cached OEM Numbers**: Pre-populate a database with common OEM numbers

### Contact Support

If issues persist after following this guide:
1. Collect Railway logs
2. Test results from `/api/test_mecaparts`
3. Environment variable configuration (without sensitive values)
4. Shopify app installation status 