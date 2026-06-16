-- ============================================
-- PHASE 4: INSTITUTIONAL INTEGRATION
-- ============================================

-- API Keys
CREATE TABLE IF NOT EXISTS api_keys (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    partner_name TEXT NOT NULL,
    partner_type TEXT CHECK (partner_type IN ('bank', 'insurance', 'dealer', 'sacco', 'fleet', 'fintech')),
    api_key TEXT UNIQUE NOT NULL,
    secret_key TEXT UNIQUE NOT NULL,
    rate_limit INTEGER DEFAULT 1000,
    monthly_requests INTEGER DEFAULT 0,
    last_used TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- API Usage
CREATE TABLE IF NOT EXISTS api_usage (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    api_key_id UUID REFERENCES api_keys(id) ON DELETE CASCADE,
    endpoint TEXT,
    request_ip TEXT,
    request_params JSONB,
    response_time INTEGER,
    status_code INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Verification Logs
CREATE TABLE IF NOT EXISTS verification_logs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    certificate_id UUID REFERENCES certificates(id) ON DELETE CASCADE,
    verified_by TEXT,
    verification_method TEXT,
    ip_address TEXT,
    user_agent TEXT,
    result TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
