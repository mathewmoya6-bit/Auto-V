# .env - Environment variables for AUTO-V

# ─── App ──────────────────────────────────────────────────────────
APP_NAME="AUTO-V Professional Valuation Engine"
APP_VERSION="2.0.0"
ENV="production"
DEBUG=false
HOST="0.0.0.0"
PORT=10000
API_V1_PREFIX="/api/v1"
PROJECT_NAME="AUTO-V API"

# ─── Database ──────────────────────────────────────────────────────
DATABASE_URL="postgresql://user:password@localhost:5432/autov"
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_TIMEOUT=30
DB_POOL_PRE_PING=true
DB_ECHO=false

# ─── Supabase ──────────────────────────────────────────────────────
SUPABASE_URL="https://tsvejnzxrxrrecgquxbq.supabase.co"
SUPABASE_ANON_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRzdmVqbnp4cnhycmVjZ3F1eGJxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODExODczNjgsImV4cCI6MjA5Njc2MzM2OH0.PCEppwafuPatBoWh4OnhzgHv6fA9uF5-bWW9mmf2VoQ"
SUPABASE_SERVICE_ROLE_KEY="your-service-role-key"
SUPABASE_JWT_SECRET="your-jwt-secret"
SUPABASE_KEY="your-supabase-key"

# ─── Security ──────────────────────────────────────────────────────
SECRET_KEY="your-secret-key-min-32-chars"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=1440
REFRESH_TOKEN_EXPIRE_DAYS=30
BCRYPT_ROUNDS=12
JWT_SECRET="your-jwt-secret-min-32-chars"
JWT_ALGORITHM="HS256"
JWT_EXPIRATION_HOURS=24

# ─── M-PESA ────────────────────────────────────────────────────────
MPESA_CONSUMER_KEY="your-mpesa-consumer-key"
MPESA_CONSUMER_SECRET="your-mpesa-consumer-secret"
MPESA_SHORTCODE="409537"
MPESA_PASSKEY="your-mpesa-passkey"
MPESA_CALLBACK_URL="https://auto-v.meipressgroup.com/api/v1/payments/mpesa/callback"
MPESA_ENVIRONMENT="production"
MPESA_ENV="production"
BASE_URL="https://auto-v.meipressgroup.com"

# ─── Vehicle Data API ──────────────────────────────────────────────
CARAPI_KEY="your-carapi-key"
CARAPI_BASE_URL="https://api.carapi.app/v1"

# ─── External API Keys ─────────────────────────────────────────────
OPENAI_API_KEY="your-openai-api-key"
GOOGLE_VISION_API_KEY="your-google-vision-api-key"

# ─── SMTP ──────────────────────────────────────────────────────────
SMTP_HOST="smtp.gmail.com"
SMTP_PORT=587
SMTP_USERNAME="your-email@gmail.com"
SMTP_PASSWORD="your-app-password"
SMTP_FROM_EMAIL="your-email@gmail.com"
SMTP_TLS=true
SMTP_SSL=false

# ─── Redis ─────────────────────────────────────────────────────────
REDIS_URL="redis://redis:6379"
REDIS_MAX_CONNECTIONS=10
REDIS_ENABLED=true
REDIS_TTL=3600

# ─── File Uploads ──────────────────────────────────────────────────
MAX_IMAGE_SIZE=10485760
MAX_DOCUMENT_SIZE=20971520
STORAGE_TYPE="supabase"
STORAGE_BUCKET="autov-storage"
UPLOAD_DIR="uploads"

# ─── CORS ──────────────────────────────────────────────────────────
CORS_ORIGINS='["https://auto-v.meipressgroup.com","https://www.auto-v.meipressgroup.com","http://localhost:3000","http://localhost:5500","http://localhost:5173","http://localhost:8000","https://auto-v.onrender.com"]'
ALLOWED_HOSTS='["auto-v.meipressgroup.com","www.auto-v.meipressgroup.com","localhost","127.0.0.1","auto-v.onrender.com"]'
