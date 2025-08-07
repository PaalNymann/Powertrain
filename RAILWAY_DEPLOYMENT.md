# Railway Deployment Guide

## Overview
This guide covers deploying the Powertrain Vehicle Parts System to Railway with PostgreSQL database support.

## Prerequisites
- Railway account
- GitHub repository with the code
- All API keys and environment variables ready

## Step 1: Create Railway Project

1. **Go to Railway Dashboard**: https://railway.app/dashboard
2. **Create New Project**: Click "New Project"
3. **Connect GitHub**: Select your repository

## Step 2: Add PostgreSQL Database

1. **Add Database Service**:
   - Click "New Service" → "Database" → "PostgreSQL"
   - Railway will automatically create a PostgreSQL database

2. **Note the Database URL**:
   - Railway will provide a `DATABASE_URL` environment variable
   - Format: `postgresql://username:password@host:port/database`

## Step 3: Deploy License Plate Service (app.py)

1. **Add Service**:
   - Click "New Service" → "GitHub Repo"
   - Select your repository

2. **Configure Service**:
   - **Name**: `license-plate-service`
   - **Root Directory**: `/` (default)
   - **Start Command**: `python app.py`

3. **Set Environment Variables**:
   ```
   # Required for SVV API
   SVV_API_KEY=your_svv_api_key_here
   SVV_ENDPOINT=https://akfell-datautlevering.atlas.vegvesen.no/enkeltoppslag/kjoretoydata
   
   # Required for Shopify and MecaParts
   SHOPIFY_DOMAIN=your_shopify_domain.myshopify.com
   SHOPIFY_TOKEN=your_shopify_token_here
   SHOPIFY_VERSION=2023-10
   
   # MecaParts API endpoint (CRITICAL for Railway)
   MECAPARTS_ENDPOINT=https://your_shopify_domain.myshopify.com/admin/api/2023-10/apps/mecaparts/api/vehicle_parts
   
   # Flask configuration
   PORT=8000
   FLASK_ENV=production
   ```

4. **Link Database**:
   - In the service settings, add the PostgreSQL database as a variable
   - Railway will automatically provide `DATABASE_URL`

## Step 4: Deploy Sync Service (sync_service.py)

1. **Add Service**:
   - Click "New Service" → "GitHub Repo"
   - Select your repository

2. **Configure Service**:
   - **Name**: `sync-service`
   - **Root Directory**: `/` (default)
   - **Start Command**: `python sync_service.py`

3. **Set Environment Variables**:
   ```
   # Rackbeat configuration
   RACKBEAT_API_KEY=your_rackbeat_token_here
   RACKBEAT_ENDPOINT=https://app.rackbeat.com/api/products
   
   # Shopify configuration
   SHOPIFY_DOMAIN=your_shopify_domain.myshopify.com
   SHOPIFY_TOKEN=your_shopify_token_here
   SHOPIFY_VERSION=2023-10
   
   # Flask configuration
   PORT=8001
   FLASK_ENV=production
   ```

## Step 5: Initialize Database

1. **Deploy Services**: Both services should deploy automatically
2. **Check Logs**: Ensure both services are running without errors
3. **Initialize Database**: The database tables will be created automatically when the app starts

## Step 6: Update Database Cache

1. **Get Service URL**: Note the Railway URL for the license plate service
2. **Update Cache**: 
   ```bash
   curl -X POST "https://your-railway-url.railway.app/api/cache/update"
   ```
3. **Check Cache Stats**:
   ```bash
   curl "https://your-railway-url.railway.app/api/cache/stats"
   ```

## Step 7: Test the Deployment

### Test License Plate Service
```bash
# Health check
curl "https://your-railway-url.railway.app/health"

# Test SVV API directly
curl "https://your-railway-url.railway.app/api/test_svv"

# Test MecaParts API directly (NEW - CRITICAL FOR DEBUGGING)
curl "https://your-railway-url.railway.app/api/test_mecaparts"

# Vehicle lookup
curl "https://your-railway-url.railway.app/api/statens_vegvesen?regnr=KH66644"

# Complete workflow
curl "https://your-railway-url.railway.app/api/car_parts_search?regnr=KH66644"

# Part number search
curl "https://your-railway-url.railway.app/api/part_number_search?part_number=TEST123"
```

### Test Sync Service
```bash
# Health check
curl "https://your-sync-service-url.railway.app/health"

# Full sync
curl -X POST "https://your-sync-service-url.railway.app/sync/full"
```

## Troubleshooting

### Common Issues

1. **Database Connection Errors**:
   - Check `DATABASE_URL` environment variable
   - Ensure PostgreSQL service is running
   - Verify database credentials

2. **Service Startup Issues**:
   - Check Railway logs for Python import errors
   - Verify all dependencies are in `requirements.txt`
   - Ensure environment variables are set correctly

3. **Cache Update Timeouts**:
   - The cache update can take time for large product catalogs
   - Consider running cache updates during off-peak hours
   - Monitor memory usage during cache updates

### MecaParts API Issues (NEW)

4. **MecaParts API Not Working on Railway**:
   - **Check Environment Variables**: Ensure `MECAPARTS_ENDPOINT` is set correctly
   - **Test Endpoint**: Use `/api/test_mecaparts` to test the API directly
   - **Check Shopify Token**: Verify `SHOPIFY_TOKEN` has admin API access
   - **Check App Installation**: Ensure MecaParts app is installed in your Shopify store
   - **Check Railway Logs**: Look for timeout or connection errors
   - **Verify Endpoint URL**: The endpoint should include `/admin/api/2023-10/` in the path

5. **MecaParts API Timeout Errors**:
   - The API call has a 30-second timeout
   - Check if the MecaParts app is responding
   - Verify network connectivity from Railway to Shopify
   - Consider increasing timeout if needed

6. **MecaParts API Authentication Errors**:
   - Verify `SHOPIFY_TOKEN` is valid and has admin API permissions
   - Check if the token has access to the MecaParts app
   - Ensure the token is not expired

## Security Considerations

1. **Environment Variables**: All sensitive data is stored in Railway environment variables
2. **Database Security**: Railway PostgreSQL is automatically secured
3. **API Keys**: Never commit API keys to the repository
4. **HTTPS**: Railway provides automatic HTTPS for all services 