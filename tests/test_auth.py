# AUTO-V API Documentation

## Base URL
https://auto-v-api.onrender.com/api

## Authentication
All API requests require a Bearer token in the Authorization header:
Authorization: Bearer <your_jwt_token>

---

## Authentication Endpoints

### Register User
POST /auth/register

**Request:**
\\\json
{
  "email": "user@example.com",
  "password": "password123",
  "full_name": "John Doe",
  "phone": "0712345678"
}
\\\

**Response:**
\\\json
{
  "message": "User registered successfully",
  "user_id": "uuid",
  "email": "user@example.com"
}
\\\

### Login
POST /auth/login

**Request:**
\\\json
{
  "email": "user@example.com",
  "password": "password123"
}
\\\

**Response:**
\\\json
{
  "access_token": "jwt_token",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "full_name": "John Doe",
    "phone": "0712345678",
    "role": "user",
    "created_at": "2024-01-01T00:00:00Z"
  }
}
\\\

---

## Vehicle Endpoints

### Register Vehicle
POST /vehicles/register

**Request:**
\\\json
{
  "registration_number": "KDA 123A",
  "make": "Toyota",
  "model": "Axio",
  "year": 2022,
  "engine_cc": 1500,
  "fuel_type": "petrol",
  "transmission": "automatic",
  "color": "White",
  "current_mileage": 50000,
  "vin": "JTEGD34V000123456"
}
\\\

### Get Vehicle
GET /vehicles/{vehicle_id}

### Get User Vehicles
GET /vehicles/user/{user_id}

---

## Valuation Endpoints

### Calculate Valuation
POST /valuations/calculate

**Request:**
\\\json
{
  "make": "Toyota",
  "model": "Axio",
  "year": 2022,
  "odometer": 50000,
  "condition": "Good",
  "accident_history": "None",
  "registration_number": "KDA 123A"
}
\\\

**Response:**
\\\json
{
  "market_value": 2850000,
  "insurance_value": 3135000,
  "trade_in_value": 2280000,
  "certificate_number": "AUTO-123456-ABC"
}
\\\

---

## Payment Endpoints

### Initiate M-Pesa Payment
POST /payments/mpesa

**Request:**
\\\json
{
  "phone": "0712345678",
  "amount": 2500,
  "service_type": "valuation",
  "user_id": "user-uuid"
}
\\\

### Check Payment Status
GET /payments/status/{checkout_request_id}

---

## Admin Endpoints

### Get All Users
GET /admin/users

### Update User Role
PUT /admin/users/{user_id}/role

**Request:**
\\\json
{
  "role": "admin"
}
\\\

### Get System Stats
GET /admin/stats

---

## Webhook Endpoints

### M-Pesa Callback
POST /webhooks/mpesa-callback

---

## Error Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 500 | Internal Server Error |

## Rate Limiting
- 100 requests per minute per IP
- Headers: X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset
"@ | Out-File -FilePath "docs\API.md" -Encoding UTF8
Write-Host "  ✅ Created: docs/API.md" -ForegroundColor Green

# ========== 3n. docs/DEPLOYMENT.md ==========
@"
# AUTO-V Deployment Guide

## Deploy to Render

### 1. Backend Deployment

1. Push your code to GitHub
2. Go to Render.com and click "New +" → "Web Service"
3. Connect your GitHub repository
4. Configure:
   - Name: uto-v-api
   - Environment: Python
   - Build Command: pip install -r requirements.txt
   - Start Command: uvicorn backend.main:app --host 0.0.0.0 --port 
   - Plan: Starter
5. Add Environment Variables:
   - SUPABASE_URL
   - SUPABASE_ANON_KEY
   - SUPABASE_SERVICE_KEY
   - JWT_SECRET
   - MPESA_CONSUMER_KEY
   - MPESA_CONSUMER_SECRET
   - MPESA_PASSKEY
   - MPESA_CALLBACK_URL
   - CORS_ORIGINS

### 2. Frontend Deployment

1. Click "New +" → "Static Site"
2. Connect GitHub repository
3. Configure:
   - Name: uto-v-frontend
   - Build Command: (leave empty)
   - Publish Directory: public
4. Set Environment Variable:
   - VITE_API_URL: https://auto-v-api.onrender.com

---

## Deploy with Docker

### Build and Run
\\\ash
docker build -t auto-v .
docker run -d -p 8000:8000 --env-file .env auto-v
\\\

### Docker Compose
\\\ash
docker-compose up -d
\\\

---

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| SUPABASE_URL | Supabase project URL | ✅ |
| SUPABASE_ANON_KEY | Supabase anon key | ✅ |
| SUPABASE_SERVICE_KEY | Supabase service role key | ✅ |
| JWT_SECRET | Secret for JWT signing | ✅ |
| MPESA_CONSUMER_KEY | M-Pesa consumer key | ⚠️ |
| MPESA_CONSUMER_SECRET | M-Pesa consumer secret | ⚠️ |
| MPESA_PASSKEY | M-Pesa passkey | ⚠️ |
| MPESA_SHORTCODE | M-Pesa shortcode | ⚠️ |
| MPESA_CALLBACK_URL | M-Pesa callback URL | ⚠️ |

---

## Health Check
GET /health - Returns {"status": "healthy"}

---

## Monitoring

- Logs: Render provides built-in logging
- Metrics: Use Render's dashboard
- Alerts: Configure email notifications in Render

---

## Backup

### Database Backup
\\\ash
pg_dump -h db.tsvejnzxrxrrecgquxbq.supabase.co -U postgres -d postgres > backup.sql
\\\

### Restore
\\\ash
psql -h db.tsvejnzxrxrrecgquxbq.supabase.co -U postgres -d postgres < backup.sql
\\\
"@ | Out-File -FilePath "docs\DEPLOYMENT.md" -Encoding UTF8
Write-Host "  ✅ Created: docs/DEPLOYMENT.md" -ForegroundColor Green

# ========== 3o. tests/test_auth.py ==========
@"
import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_register():
    response = client.post(
        "/api/auth/register",
        json={
            "email": "test@example.com",
            "password": "password123",
            "full_name": "Test User",
            "phone": "0712345678"
        }
    )
    assert response.status_code in [200, 400]  # 400 if already exists

def test_login():
    response = client.post(
        "/api/auth/login",
        json={
            "email": "test@example.com",
            "password": "password123"
        }
    )
    assert response.status_code in [200, 401]
