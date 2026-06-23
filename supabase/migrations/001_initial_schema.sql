-- ============================================
-- AUTO-V PRODUCTION DATABASE SCHEMA (COMPLETE)
-- ============================================

-- ============================================
-- 1. USER PROFILES
-- ============================================
CREATE TABLE IF NOT EXISTS user_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    full_name TEXT,
    phone TEXT,
    role TEXT DEFAULT 'user',
    company TEXT,
    verified BOOLEAN DEFAULT FALSE,
    first_login BOOLEAN DEFAULT TRUE,
    has_vehicle BOOLEAN DEFAULT FALSE,
    login_count INTEGER DEFAULT 0,
    client_type TEXT DEFAULT 'individual',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_login TIMESTAMPTZ
);

-- ============================================
-- 2. PAYMENTS TABLE (CRITICAL - WAS MISSING!)
-- ============================================
CREATE TABLE IF NOT EXISTS payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    payment_id VARCHAR(50) UNIQUE NOT NULL,
    user_id UUID REFERENCES user_profiles(id),
    valuation_id UUID,
    request_id VARCHAR(100),
    amount DECIMAL(10, 2) NOT NULL,
    phone VARCHAR(20),
    mpesa_phone VARCHAR(20),
    merchant_request_id VARCHAR(100),
    checkout_request_id VARCHAR(100) UNIQUE,
    mpesa_code VARCHAR(50),
    transaction_id VARCHAR(50),
    status VARCHAR(20) DEFAULT 'pending',
    payment_method VARCHAR(20) DEFAULT 'mpesa',
    mpesa_result_code VARCHAR(10),
    mpesa_result_desc TEXT,
    payment_data JSONB DEFAULT '{}'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    paid_at TIMESTAMPTZ
);

-- ============================================
-- 3. SERVICE REQUESTS
-- ============================================
CREATE TABLE IF NOT EXISTS service_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES user_profiles(id),
    service_type TEXT NOT NULL,
    purpose TEXT,
    status TEXT DEFAULT 'pending',
    reference TEXT UNIQUE,
    payment_id VARCHAR(50) REFERENCES payments(payment_id),
    vehicle_id UUID,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- ============================================
-- 4. VEHICLES
-- ============================================
CREATE TABLE IF NOT EXISTS vehicles (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES user_profiles(id),
    registration_number TEXT UNIQUE,
    chassis_number TEXT,
    vin_number TEXT,
    make TEXT NOT NULL,
    model TEXT NOT NULL,
    year INTEGER NOT NULL,
    engine_cc INTEGER,
    fuel_type TEXT CHECK (fuel_type IN ('petrol', 'diesel', 'hybrid', 'electric')),
    transmission TEXT CHECK (transmission IN ('manual', 'automatic', 'cvt')),
    color TEXT,
    current_mileage INTEGER DEFAULT 0,
    status TEXT DEFAULT 'active',
    last_inspection_date DATE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- 5. VALUATIONS
-- ============================================
CREATE TABLE IF NOT EXISTS valuations (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    vehicle_id UUID REFERENCES vehicles(id),
    user_id UUID REFERENCES user_profiles(id),
    valuation_date DATE NOT NULL,
    market_value DECIMAL(12,2),
    insurance_value DECIMAL(12,2),
    trade_in_value DECIMAL(12,2),
    forced_sale_value DECIMAL(12,2),
    certificate_number TEXT UNIQUE,
    qr_code TEXT,
    status TEXT DEFAULT 'draft',
    service_request_id UUID REFERENCES service_requests(id),
    payment_id VARCHAR(50) REFERENCES payments(payment_id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- 6. INSPECTIONS
-- ============================================
CREATE TABLE IF NOT EXISTS inspections (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    vehicle_id UUID REFERENCES vehicles(id),
    user_id UUID REFERENCES user_profiles(id),
    inspection_date DATE NOT NULL,
    inspector_name TEXT,
    condition_rating INTEGER CHECK (condition_rating BETWEEN 1 AND 10),
    findings TEXT,
    recommendations TEXT,
    status TEXT DEFAULT 'draft',
    service_request_id UUID REFERENCES service_requests(id),
    payment_id VARCHAR(50) REFERENCES payments(payment_id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- 7. ASSESSMENTS
-- ============================================
CREATE TABLE IF NOT EXISTS assessments (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    vehicle_id UUID REFERENCES vehicles(id),
    user_id UUID REFERENCES user_profiles(id),
    assessment_type TEXT,
    damage_estimate DECIMAL(12,2),
    repair_cost DECIMAL(12,2),
    total_loss BOOLEAN DEFAULT FALSE,
    salvage_value DECIMAL(12,2),
    findings TEXT,
    status TEXT DEFAULT 'draft',
    service_request_id UUID REFERENCES service_requests(id),
    payment_id VARCHAR(50) REFERENCES payments(payment_id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- 8. MILEAGE RATES
-- ============================================
CREATE TABLE IF NOT EXISTS mileage_rates (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    vehicle_category TEXT NOT NULL,
    rate_per_km DECIMAL(10,2) NOT NULL,
    effective_from DATE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- 9. MILEAGE CLAIMS
-- ============================================
CREATE TABLE IF NOT EXISTS mileage_claims (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES user_profiles(id),
    employee_name TEXT,
    trip_date DATE NOT NULL,
    start_location TEXT,
    end_location TEXT,
    purpose TEXT,
    start_odometer INTEGER,
    end_odometer INTEGER,
    distance_km INTEGER,
    rate_per_km DECIMAL(10,2),
    claim_amount DECIMAL(10,2),
    status TEXT DEFAULT 'pending',
    approved_by UUID REFERENCES user_profiles(id),
    approval_date TIMESTAMPTZ,
    service_request_id UUID REFERENCES service_requests(id),
    payment_id VARCHAR(50) REFERENCES payments(payment_id),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- 10. SYSTEM SETTINGS
-- ============================================
CREATE TABLE IF NOT EXISTS system_settings (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    setting_key TEXT UNIQUE NOT NULL,
    setting_value TEXT NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- 11. NOTIFICATIONS
-- ============================================
CREATE TABLE IF NOT EXISTS notifications (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES user_profiles(id),
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    type TEXT DEFAULT 'info',
    read BOOLEAN DEFAULT FALSE,
    data JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    read_at TIMESTAMPTZ
);

-- ============================================
-- 12. INDEXES (Performance)
-- ============================================
CREATE INDEX IF NOT EXISTS idx_payments_payment_id ON payments(payment_id);
CREATE INDEX IF NOT EXISTS idx_payments_checkout_request_id ON payments(checkout_request_id);
CREATE INDEX IF NOT EXISTS idx_payments_user_id ON payments(user_id);
CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status);
CREATE INDEX IF NOT EXISTS idx_payments_mpesa_code ON payments(mpesa_code);
CREATE INDEX IF NOT EXISTS idx_payments_created_at ON payments(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_service_requests_user_id ON service_requests(user_id);
CREATE INDEX IF NOT EXISTS idx_service_requests_status ON service_requests(status);
CREATE INDEX IF NOT EXISTS idx_service_requests_payment_id ON service_requests(payment_id);

CREATE INDEX IF NOT EXISTS idx_vehicles_user_id ON vehicles(user_id);
CREATE INDEX IF NOT EXISTS idx_vehicles_registration ON vehicles(registration_number);

CREATE INDEX IF NOT EXISTS idx_valuations_user_id ON valuations(user_id);
CREATE INDEX IF NOT EXISTS idx_valuations_vehicle_id ON valuations(vehicle_id);

CREATE INDEX IF NOT EXISTS idx_mileage_claims_user_id ON mileage_claims(user_id);
CREATE INDEX IF NOT EXISTS idx_mileage_claims_status ON mileage_claims(status);

-- ============================================
-- 13. TRIGGERS
-- ============================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_user_profiles_updated_at
    BEFORE UPDATE ON user_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_payments_updated_at
    BEFORE UPDATE ON payments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_service_requests_updated_at
    BEFORE UPDATE ON service_requests
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_vehicles_updated_at
    BEFORE UPDATE ON vehicles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_system_settings_updated_at
    BEFORE UPDATE ON system_settings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- 14. DEFAULT DATA
-- ============================================
INSERT INTO system_settings (setting_key, setting_value) VALUES
('instant_fee', '500'),
('valuation_fee', '2500'),
('inspection_fee', '3500'),
('assessment_fee', '3000'),
('mileage_fee', '1500'),
('fleet_fee', '4000'),
('verification_fee', '1000')
ON CONFLICT (setting_key) DO NOTHING;

INSERT INTO mileage_rates (vehicle_category, rate_per_km, effective_from, is_active) VALUES
('Small Hatchback', 22, '2024-01-01', true),
('Compact Sedan', 28, '2024-01-01', true),
('Midsize Sedan', 35, '2024-01-01', true),
('SUV/Crossover', 42, '2024-01-01', true),
('Large SUV', 55, '2024-01-01', true),
('Pickup Truck', 48, '2024-01-01', true),
('Motorcycle', 12, '2024-01-01', true)
ON CONFLICT DO NOTHING;

-- ============================================
-- 15. RLS POLICIES
-- ============================================
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE service_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE vehicles ENABLE ROW LEVEL SECURITY;
ALTER TABLE valuations ENABLE ROW LEVEL SECURITY;
ALTER TABLE inspections ENABLE ROW LEVEL SECURITY;
ALTER TABLE assessments ENABLE ROW LEVEL SECURITY;
ALTER TABLE mileage_claims ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;

-- User Profiles
DROP POLICY IF EXISTS "Users can view own profile" ON user_profiles;
CREATE POLICY "Users can view own profile" ON user_profiles
    FOR SELECT USING (auth.uid() = id);

DROP POLICY IF EXISTS "Users can update own profile" ON user_profiles;
CREATE POLICY "Users can update own profile" ON user_profiles
    FOR UPDATE USING (auth.uid() = id);

-- Payments
DROP POLICY IF EXISTS "Users can view own payments" ON payments;
CREATE POLICY "Users can view own payments" ON payments
    FOR SELECT USING (auth.uid() = user_id OR user_id IS NULL);

DROP POLICY IF EXISTS "Users can insert payments" ON payments;
CREATE POLICY "Users can insert payments" ON payments
    FOR INSERT WITH CHECK (auth.uid() = user_id OR user_id IS NULL);

DROP POLICY IF EXISTS "Service role has full access" ON payments;
CREATE POLICY "Service role has full access" ON payments
    USING (true);

-- Service Requests
DROP POLICY IF EXISTS "Users can view own service requests" ON service_requests;
CREATE POLICY "Users can view own service requests" ON service_requests
    FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert service requests" ON service_requests;
CREATE POLICY "Users can insert service requests" ON service_requests
    FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Vehicles
DROP POLICY IF EXISTS "Users can view own vehicles" ON vehicles;
CREATE POLICY "Users can view own vehicles" ON vehicles
    FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert own vehicles" ON vehicles;
CREATE POLICY "Users can insert own vehicles" ON vehicles
    FOR INSERT WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can update own vehicles" ON vehicles;
CREATE POLICY "Users can update own vehicles" ON vehicles
    FOR UPDATE USING (auth.uid() = user_id);

-- Valuations
DROP POLICY IF EXISTS "Users can view own valuations" ON valuations;
CREATE POLICY "Users can view own valuations" ON valuations
    FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert own valuations" ON valuations;
CREATE POLICY "Users can insert own valuations" ON valuations
    FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Mileage Claims
DROP POLICY IF EXISTS "Users can view own claims" ON mileage_claims;
CREATE POLICY "Users can view own claims" ON mileage_claims
    FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert own claims" ON mileage_claims;
CREATE POLICY "Users can insert own claims" ON mileage_claims
    FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Notifications
DROP POLICY IF EXISTS "Users can view own notifications" ON notifications;
CREATE POLICY "Users can view own notifications" ON notifications
    FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can update own notifications" ON notifications;
CREATE POLICY "Users can update own notifications" ON notifications
    FOR UPDATE USING (auth.uid() = user_id);

-- ============================================
-- 16. VERIFICATION QUERY
-- ============================================
SELECT 
    tablename,
    '✅' as status
FROM pg_tables 
WHERE schemaname = 'public' 
    AND tablename IN (
        'user_profiles', 'payments', 'service_requests', 
        'vehicles', 'valuations', 'inspections', 'assessments',
        'mileage_rates', 'mileage_claims', 'system_settings', 'notifications'
    )
ORDER BY tablename;
