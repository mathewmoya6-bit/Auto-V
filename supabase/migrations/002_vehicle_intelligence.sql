-- ============================================
-- PHASE 2: VEHICLE INTELLIGENCE DATABASE
-- Complete Production Schema
-- ============================================

-- Vehicle Intelligence Master
CREATE TABLE IF NOT EXISTS vehicle_intelligence (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    registration_number TEXT UNIQUE NOT NULL,
    vin TEXT,
    make TEXT NOT NULL,
    model TEXT NOT NULL,
    year INTEGER NOT NULL,
    engine_cc INTEGER,
    fuel_type TEXT,
    transmission TEXT,
    color TEXT,
    county TEXT,
    current_mileage INTEGER DEFAULT 0,
    last_valuation_date DATE,
    last_inspection_date DATE,
    valuation_count INTEGER DEFAULT 0,
    inspection_count INTEGER DEFAULT 0,
    average_valuation DECIMAL(12,2),
    highest_valuation DECIMAL(12,2),
    lowest_valuation DECIMAL(12,2),
    condition_score DECIMAL(5,2),
    risk_score DECIMAL(5,2),
    risk_level TEXT CHECK (risk_level IN ('Low', 'Medium', 'High', 'Critical')),
    market_trend TEXT CHECK (market_trend IN ('Appreciating', 'Stable', 'Depreciating')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Vehicle History Reports
CREATE TABLE IF NOT EXISTS vehicle_history_reports (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    vehicle_id UUID REFERENCES vehicle_intelligence(id) ON DELETE CASCADE,
    report_number TEXT UNIQUE,
    report_type TEXT CHECK (report_type IN ('Full', 'Valuation', 'Inspection', 'Risk', 'Market')),
    generated_by UUID REFERENCES user_profiles(id),
    report_data JSONB,
    pdf_url TEXT,
    views INTEGER DEFAULT 0,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Risk Indicators
CREATE TABLE IF NOT EXISTS risk_indicators (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    vehicle_id UUID REFERENCES vehicle_intelligence(id) ON DELETE CASCADE,
    indicator_type TEXT CHECK (indicator_type IN ('accident', 'theft', 'fraud', 'flood', 'fire', 'odometer_fraud', 'ownership', 'financial')),
    severity TEXT CHECK (severity IN ('Low', 'Medium', 'High', 'Critical')),
    description TEXT,
    evidence TEXT,
    reported_date DATE,
    verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- County Statistics
CREATE TABLE IF NOT EXISTS county_stats (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    county TEXT NOT NULL,
    total_vehicles INTEGER DEFAULT 0,
    average_value DECIMAL(12,2),
    most_popular_make TEXT,
    most_popular_model TEXT,
    average_age DECIMAL(5,2),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Fleet Vehicles
CREATE TABLE IF NOT EXISTS fleet_vehicles (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    organization_id UUID,
    vehicle_id UUID REFERENCES vehicles(id) ON DELETE CASCADE,
    assigned_driver TEXT,
    department TEXT,
    purchase_date DATE,
    purchase_price DECIMAL(12,2),
    expected_life_years INTEGER DEFAULT 5,
    current_depreciation DECIMAL(12,2),
    maintenance_alerts JSONB,
    next_service_date DATE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Dealer Inventory
CREATE TABLE IF NOT EXISTS dealer_inventory (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    dealer_id UUID REFERENCES user_profiles(id),
    vehicle_id UUID REFERENCES vehicles(id) ON DELETE CASCADE,
    listed_price DECIMAL(12,2),
    days_on_lot INTEGER DEFAULT 0,
    demand_score DECIMAL(5,2),
    status TEXT CHECK (status IN ('available', 'sold', 'reserved', 'auction')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_vehicle_intelligence_registration ON vehicle_intelligence(registration_number);
CREATE INDEX IF NOT EXISTS idx_vehicle_intelligence_make_model ON vehicle_intelligence(make, model);
CREATE INDEX IF NOT EXISTS idx_vehicle_intelligence_county ON vehicle_intelligence(county);
