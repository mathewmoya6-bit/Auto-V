// ============================================
// AUTO-V PRODUCTION CONFIGURATION
// ============================================

const CONFIG = {
    // App Settings
    APP_NAME: "AUTO-V",
    APP_VERSION: "2.0.0",
    APP_URL: window.location.origin,
    
    // Supabase Configuration
    SUPABASE_URL: "https://tsvejnzxrxrrecgquxbq.supabase.co",
    SUPABASE_ANON_KEY: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRzdmVqbnp4cnhycmVjZ3F1eGJxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODExODczNjgsImV4cCI6MjA5Njc2MzM2OH0.PCEppwafuPatBoWh4OnhzgHv6fA9uF5-bWW9mmf2VoQ",
    
    // M-Pesa Configuration (Add your Daraja API credentials)
    MPESA: {
        CONSUMER_KEY: "",  // Add from Safaricom Daraja
        CONSUMER_SECRET: "", // Add from Safaricom Daraja
        PASSKEY: "", // Add from Safaricom Daraja
        SHORTCODE: "4095377",
        CALLBACK_URL: `${window.location.origin}/api/mpesa/callback`,
        ENVIRONMENT: "sandbox" // sandbox or production
    },
    
    // Email Configuration (using Resend or SendGrid)
    EMAIL: {
        FROM: "noreply@auto-v.com",
        API_KEY: "", // Add your email API key
        SERVICE: "resend" // resend, sendgrid, or smtp
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
        ENABLE_MPESA: false,  // Set true when M-Pesa configured
        ENABLE_EMAIL: false,   // Set true when email configured
        ENABLE_PWA: true,      // Progressive Web App
        ENABLE_OFFLINE: true,  // Offline mode
        ENABLE_NOTIFICATIONS: true  // Push notifications
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
