// ============================================
// AUTO-V PRODUCTION CONFIGURATION
// Domain: https://auto-v.meipressgroup.com
// ============================================

const CONFIG = {
    // App Settings
    APP_NAME: "AUTO-V",
    APP_VERSION: "3.0.0",
    APP_URL: "https://auto-v.meipressgroup.com",
    API_URL: "https://auto-v.meipressgroup.com/api",
    
    // Supabase Configuration
    SUPABASE_URL: "https://tsvejnzxrxrrecgquxbq.supabase.co",
    SUPABASE_ANON_KEY: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRzdmVqbnp4cnhycmVjZ3F1eGJxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODExODczNjgsImV4cCI6MjA5Njc2MzM2OH0.PCEppwafuPatBoWh4OnhzgHv6fA9uF5-bWW9mmf2VoQ",
    
    // M-Pesa Configuration (Production)
    MPESA: {
        CONSUMER_KEY: "LI2gcJZEheN8qCfXHEXV4gdYXvOBHVnv",
        CONSUMER_SECRET: "aGGo8AuPJVpsZLcs",
        PASSKEY: "7eb17a031bdfd5b4251863a1ddb72c5b9cd14f3385aa6a258c1442a0116e8277",
        SHORTCODE: "4095377",
        CALLBACK_URL: "https://auto-v.meipressgroup.com/api/mpesa/callback",
        ENVIRONMENT: "production"
    },
    
    // Feature Flags
    FEATURES: {
        ENABLE_MPESA: true,
        ENABLE_EMAIL: false,
        ENABLE_PWA: true
    },
    
    // Pricing
    PRICING: {
        VALUATION_FEE: 2500,
        INSPECTION_FEE: 3500,
        MILEAGE_RATES: {
            'Small Hatchback': 22,
            'Compact Sedan': 28,
            'Midsize Sedan': 35,
            'SUV/Crossover': 42,
            'Large SUV': 55,
            'Pickup Truck': 48,
            'Minibus': 65,
            'Motorcycle': 12
        }
    },
    
    // Support
    SUPPORT: {
        PHONE: "+254 700 000 000",
        EMAIL: "support@auto-v.com",
        WEBSITE: "https://auto-v.meipressgroup.com"
    }
};

if (typeof module !== 'undefined' && module.exports) {
    module.exports = CONFIG;
}
