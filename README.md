# Powertrain Vehicle Parts System

A comprehensive vehicle parts search system that allows customers to find compatible parts by license plate number.

## Features

- **License Plate Search**: Enter a Norwegian license plate to find compatible parts
- **Vehicle Information**: Automatic vehicle lookup from Statens Vegvesen
- **Parts Matching**: Find parts using TecDoc OEM numbers
- **Fast Database Search**: Optimized database queries for quick results
- **Shopify Integration**: Syncs with Shopify product catalog

## API Endpoints

### License Plate Search
```
GET /api/car_parts_search?regnr=KH66644
```

### Direct Part Number Search
```
GET /api/part_number_search?part_number=W7508629
```

### Database Cache Management
```
GET /api/cache/stats
POST /api/cache/update
```

### Health Check
```
GET /health
```

## Environment Variables

```bash
# Database
DATABASE_URL=postgresql://username:password@host:port/database

# APIs
SVV_API_KEY=your_svv_api_key_here
RACKBEAT_API_KEY=your_rackbeat_token_here
SHOPIFY_DOMAIN=your_shopify_domain.myshopify.com
SHOPIFY_TOKEN=your_shopify_token_here

# Flask
PORT_APP=8000
PORT_SYNC=8001
```

## Installation

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Set environment variables
4. Run: `python app.py`

## Database Setup

The system uses PostgreSQL in production and SQLite locally. Database tables are created automatically on startup.

## Deployment

See `RAILWAY_DEPLOYMENT.md` for Railway deployment instructions. 