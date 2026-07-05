// ============================================================
// AUTO-V FRONTEND CONFIGURATION
// ============================================================

const APP_CONFIG = {
    VERSION: '3.1.0',
    ENV: 'production',
    COMPANY: 'AUTO-V Kenya',
    CONTACT_EMAIL: 'support@autov.africa',
    CONTACT_PHONE: '+254 700 000 000',
    M_PESA_PAYBILL: '4095377',
    M_PESA_ACCOUNT: 'AUTO-V'
};

// Feature flags
const FEATURES = {
    ENABLE_MPESA: true,
    ENABLE_AI_VALUATION: true,
    ENABLE_INSPECTION: true,
    ENABLE_ASSESSMENT: true,
    ENABLE_CERTIFICATES: true,
    ENABLE_REPORTS: true,
    ENABLE_REALTIME: true,
    ENABLE_OFFLINE_MODE: true,
    ENABLE_PUSH_NOTIFICATIONS: false
};

// Service pricing defaults
const SERVICE_PRICES = {
    instant_fee: 500,
    valuation_fee: 2500,
    inspection_fee: 3500,
    assessment_fee: 3000,
    mileage_fee: 1000,
    fleet_fee: 5000,
    verification_fee: 750
};

// API Endpoints
const API_ENDPOINTS = {
    AUTH: {
        LOGIN: '/auth/login',
        LOGOUT: '/auth/logout',
        REGISTER: '/auth/register',
        ME: '/auth/me',
        CHANGE_PASSWORD: '/auth/change-password',
        RESET_PASSWORD: '/auth/reset-password'
    },
    USERS: {
        PROFILE: '/users/profile',
        STATS: '/users/stats',
        SETTINGS: '/users/settings',
        EXPORT: '/users/export-data'
    },
    VEHICLES: {
        LIST: '/vehicles',
        COUNT: '/vehicles/count',
        MODELS: '/vehicles/models',
        DECODE_VIN: '/vehicles/decode-vin'
    },
    VALUATIONS: {
        LIST: '/valuations',
        INSTANT: '/valuations/instant',
        TOTAL: '/valuations/total'
    },
    INSPECTIONS: {
        LIST: '/inspections',
        CREATE: '/inspections'
    },
    ASSESSMENTS: {
        CREATE: '/assessments/create'
    },
    CERTIFICATES: {
        LIST: '/certificates',
        COUNT: '/certificates/count',
        VIEW: '/certificates/view',
        DOWNLOAD: '/certificates/download'
    },
    REQUESTS: {
        LIST: '/service-requests',
        COUNT: '/service-requests/count',
        PAYMENT: '/service-requests/:id/payment'
    },
    REPORTS: {
        GENERATE: '/reports/generate',
        DOWNLOAD: '/reports/download'
    },
    PAYMENTS: {
        CREATE: '/payments',
        STATUS: '/payments/:id/status',
        INITIATE: '/payments/:id/initiate'
    },
    ADMIN: {
        STATS: '/admin/stats',
        USERS: '/admin/users',
        REQUESTS: '/admin/requests',
        PAYMENTS: '/admin/payments',
        SERVICES: '/admin/services',
        SETTINGS: '/admin/settings',
        FEES: '/admin/fees'
    },
    SETTINGS: {
        FEES: '/services/fees',
        INSTANT_FEE: '/settings/instant_fee'
    },
    FUEL: {
        PRICES: '/fuel_prices'
    }
};

// Local storage keys
const STORAGE_KEYS = {
    ACCESS_TOKEN: 'access_token',
    USER: 'autoV_user',
    SETTINGS: 'autov_settings',
    PREFERENCES: 'user_preferences',
    DRAFT: 'valuationDraft'
};

// Export configuration
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        APP_CONFIG,
        FEATURES,
        SERVICE_PRICES,
        API_ENDPOINTS,
        STORAGE_KEYS
    };
}
