-- ============================================
-- AUTO-V COMPLETE DATABASE SCHEMA
-- ============================================

-- Users
CREATE TABLE IF NOT EXISTS user_profiles (
    id TEXT PRIMARY KEY,
    email TEXT,
    full_name TEXT,
    phone TEXT,
    role TEXT DEFAULT 'user',
    company TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Vehicles
CREATE TABLE IF NOT EXISTS vehicles (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id TEXT REFERENCES user_profiles(id),
    registration_number TEXT UNIQUE,
    chassis_number TEXT,
    make TEXT NOT NULL,
    model TEXT NOT NULL,
    year INTEGER NOT NULL,
    engine_cc INTEGER,
    fuel_type TEXT,
    transmission TEXT,
    color TEXT,
    current_mileage INTEGER DEFAULT 0,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Valuations
CREATE TABLE IF NOT EXISTS valuations (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    vehicle_id UUID REFERENCES vehicles(id),
    valuer_id TEXT REFERENCES user_profiles(id),
    valuation_date DATE NOT NULL,
    market_value DECIMAL(12,2),
    insurance_value DECIMAL(12,2),
    trade_in_value DECIMAL(12,2),
    forced_sale_value DECIMAL(12,2),
    certificate_number TEXT UNIQUE,
    qr_code TEXT,
    status TEXT DEFAULT 'draft',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Mileage Claims
CREATE TABLE IF NOT EXISTS mileage_claims (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id TEXT REFERENCES user_profiles(id),
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
    approved_by TEXT,
    approval_date TIMESTAMPTZ,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Mileage Rates
CREATE TABLE IF NOT EXISTS mileage_rates (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    vehicle_category TEXT NOT NULL,
    rate_per_km DECIMAL(10,2) NOT NULL,
    effective_from DATE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- System Settings
CREATE TABLE IF NOT EXISTS system_settings (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    setting_key TEXT UNIQUE NOT NULL,
    setting_value TEXT NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert default data
INSERT INTO system_settings (setting_key, setting_value) VALUES
('valuation_fee', '2500'),
('inspection_fee', '3500')
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
