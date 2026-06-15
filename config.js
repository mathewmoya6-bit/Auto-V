// ============================================
// AUTO-V PRODUCTION CONFIGURATION
// WITH M-PESA DARAJA API CREDENTIALS
// ============================================

const CONFIG = {
    // App Settings
    APP_NAME: "AUTO-V",
    APP_VERSION: "3.0.0",
    APP_URL: window.location.origin,
    
    // Supabase Configuration
    SUPABASE_URL: "https://tsvejnzxrxrrecgquxbq.supabase.co",
    SUPABASE_ANON_KEY: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRzdmVqbnp4cnhycmVjZ3F1eGJxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODExODczNjgsImV4cCI6MjA5Njc2MzM2OH0.PCEppwafuPatBoWh4OnhzgHv6fA9uF5-bWW9mmf2VoQ",
    
    // M-Pesa Configuration (Production Credentials)
    MPESA: {
        CONSUMER_KEY: "LI2gcJZEheN8qCfXHEXV4gdYXvOBHVnv",
        CONSUMER_SECRET: "aGGo8AuPJVpsZLcs",
        PASSKEY: "7eb17a031bdfd5b4251863a1ddb72c5b9cd14f3385aa6a258c1442a0116e8277",
        SHORTCODE: "4095377",
        CALLBACK_URL: `${window.location.origin}/api/mpesa/callback`,
        ENVIRONMENT: "production",  // Set to production for live payments
        ACCOUNT_TYPE: "PayBill"  // PayBill or TillNumber
    },
    
    // Email Configuration
    EMAIL: {
        FROM: "noreply@auto-v.com",
        API_KEY: "", // Add your Resend/SendGrid API key
        SERVICE: "resend"
    },
    
    // Supabase Storage Buckets
    STORAGE: {
        VEHICLE_PHOTOS: "vehicle-photos",
        INSPECTION_PHOTOS: "inspection-photos",
        RECEIPTS: "receipts",
        CERTIFICATES: "certificates"
    },
    
    // Feature Flags
    FEATURES: {
        ENABLE_MPESA: true,   // ✅ M-Pesa is now enabled
        ENABLE_EMAIL: false,
        ENABLE_PWA: true,
        ENABLE_OFFLINE: true,
        ENABLE_NOTIFICATIONS: true
    },
    
    // Rate Limits
    LIMITS: {
        MAX_CLAIMS_PER_DAY: 5,
        MAX_VALUATIONS_PER_DAY: 10,
        MAX_DISTANCE_PER_CLAIM: 1000,
        MAX_CLAIM_AMOUNT: 50000,
        MAX_PHOTOS_PER_REQUEST: 10
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
        WHATSAPP: "https://wa.me/254700000000"
    }
};

// Freeze configuration
Object.freeze(CONFIG);

// Export
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CONFIG;
}
