-- ============================================
-- PHASE 3: AI LAYER
-- ============================================

-- AI Damage Detection
CREATE TABLE IF NOT EXISTS ai_damage_detection (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    vehicle_id UUID REFERENCES vehicles(id) ON DELETE CASCADE,
    image_url TEXT NOT NULL,
    photo_type TEXT,
    damage_type TEXT CHECK (damage_type IN ('dent', 'scratch', 'broken_light', 'paint_damage', 'tyre_wear', 'rust', 'crack')),
    confidence_score DECIMAL(5,2),
    severity TEXT CHECK (severity IN ('Minor', 'Moderate', 'Severe')),
    repair_cost_estimate DECIMAL(10,2),
    detected_at TIMESTAMPTZ DEFAULT NOW(),
    processed BOOLEAN DEFAULT FALSE
);

-- AI Valuations
CREATE TABLE IF NOT EXISTS ai_valuations (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    vehicle_id UUID REFERENCES vehicles(id) ON DELETE CASCADE,
    query_text TEXT,
    suggested_value DECIMAL(12,2),
    confidence_score DECIMAL(5,2),
    valuation_factors JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Predictive Pricing
CREATE TABLE IF NOT EXISTS predictive_pricing (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    vehicle_id UUID REFERENCES vehicles(id) ON DELETE CASCADE,
    current_value DECIMAL(12,2),
    forecast_3_months DECIMAL(12,2),
    forecast_6_months DECIMAL(12,2),
    forecast_12_months DECIMAL(12,2),
    confidence_score DECIMAL(5,2),
    last_updated TIMESTAMPTZ DEFAULT NOW()
);
