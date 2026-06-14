// supabase.js - Production with REAL M-PESA
const SUPABASE_URL = "https://tsvejnzxrxrrecgquxbq.supabase.co";
const SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRzdmVqbnp4cnhycmVjZ3F1eGJxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODExODczNjgsImV4cCI6MjA5Njc2MzM2OH0.PCEppwafuPatBoWh4OnhzgHv6fA9uF5-bWW9mmf2VoQ";

// REAL M-PESA PRODUCTION CREDENTIALS
const MPESA_CONFIG = {
    consumerKey: "LI2gcJZEheN8qCfXHEXV4gdYXvOBHVnv",
    consumerSecret: "aGGo8AuPJVpsZLcs",
    passkey: "7eb17a031bdfd5b4251863a1ddb72c5b9cd14f3385aa6a258c1442a0116e8277",
    shortcode: "4095377",
    callbackUrl: "https://tsvejnzxrxrrecgquxbq.supabase.co/functions/v1/mpesa-callback"
};

const supabase = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

// Auth functions
async function requireAuth() {
    const { data: { user }, error } = await supabase.auth.getUser();
    if (error || !user) {
        window.location.href = "login.html";
        return null;
    }
    return user;
}

async function logout() {
    await supabase.auth.signOut();
    window.location.href = "login.html";
}

// Get M-Pesa access token
async function getMpesaAccessToken() {
    const auth = btoa(`${MPESA_CONFIG.consumerKey}:${MPESA_CONFIG.consumerSecret}`);
    const response = await fetch('https://api.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials', {
        method: 'GET',
        headers: { 'Authorization': `Basic ${auth}` }
    });
    const data = await response.json();
    return data.access_token;
}

// Initiate REAL M-Pesa STK Push
async function initiateMpesaPayment(phoneNumber, amount, accountReference, transactionDesc) {
    try {
        const accessToken = await getMpesaAccessToken();
        
        const timestamp = new Date().toISOString().replace(/[^0-9]/g, '').slice(0, 14);
        const password = btoa(`${MPESA_CONFIG.shortcode}${MPESA_CONFIG.passkey}${timestamp}`);
        
        // Format phone number to 254XXXXXXXXX
        let formattedPhone = phoneNumber.replace(/\D/g, '');
        if (formattedPhone.startsWith('0')) {
            formattedPhone = '254' + formattedPhone.substring(1);
        }
        if (!formattedPhone.startsWith('254')) {
            formattedPhone = '254' + formattedPhone;
        }
        
        const requestBody = {
            BusinessShortCode: MPESA_CONFIG.shortcode,
            Password: password,
            Timestamp: timestamp,
            TransactionType: 'CustomerPayBillOnline',
            Amount: amount,
            PartyA: formattedPhone,
            PartyB: MPESA_CONFIG.shortcode,
            PhoneNumber: formattedPhone,
            CallBackURL: MPESA_CONFIG.callbackUrl,
            AccountReference: accountReference.substring(0, 12),
            TransactionDesc: transactionDesc.substring(0, 13)
        };
        
        console.log('Initiating M-Pesa STK Push:', requestBody);
        
        const response = await fetch('https://api.safaricom.co.ke/mpesa/stkpush/v1/processrequest', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${accessToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestBody)
        });
        
        const result = await response.json();
        console.log('M-Pesa Response:', result);
        
        return result;
        
    } catch (error) {
        console.error('M-Pesa Error:', error);
        return { ResponseCode: '1', ResponseDescription: error.message };
    }
}

// Create service request
async function createServiceRequest(data) {
    const { data: request, error } = await supabase
        .from('service_requests')
        .insert({
            user_id: data.user_id,
            service_type: data.service_type,
            registration_number: data.registration_number,
            make: data.make,
            model: data.model,
            year: data.year,
            purpose: data.purpose,
            mileage: data.mileage,
            amount: data.amount,
            phone: data.phone,
            payment_status: 'pending',
            status: 'awaiting_payment'
        })
        .select()
        .single();
    
    if (error) throw error;
    return request;
}

// Get service requests
async function getServiceRequests(userId) {
    const { data, error } = await supabase
        .from('service_requests')
        .select('*')
        .eq('user_id', userId)
        .order('created_at', { ascending: false });
    
    if (error) throw error;
    return data;
}

// Load fees
async function loadFees() {
    try {
        const { data: valuationFee } = await supabase
            .from('system_settings')
            .select('setting_value')
            .eq('setting_key', 'valuation_fee')
            .single();
        
        const { data: inspectionFee } = await supabase
            .from('system_settings')
            .select('setting_value')
            .eq('setting_key', 'inspection_fee')
            .single();
        
        return {
            valuationFee: valuationFee ? parseInt(valuationFee.setting_value) : 2500,
            inspectionFee: inspectionFee ? parseInt(inspectionFee.setting_value) : 3500
        };
    } catch (e) {
        return { valuationFee: 2500, inspectionFee: 3500 };
    }
}

// Main payment function
async function initiatePayment(serviceId, amount, phone, reference, serviceType) {
    const result = await initiateMpesaPayment(phone, amount, reference, `AUTO-V ${serviceType}`);
    
    if (result.ResponseCode === '0') {
        // Store checkout request ID
        await supabase
            .from('service_requests')
            .update({ mpesa_checkout_request_id: result.CheckoutRequestID })
            .eq('id', serviceId);
    }
    
    return result;
}

// Check payment status
async function checkPaymentStatus(serviceId) {
    const { data, error } = await supabase
        .from('service_requests')
        .select('payment_status, status, result')
        .eq('id', serviceId)
        .single();
    
    if (error) throw error;
    return data;
}

// Subscribe to realtime updates
function subscribeToServiceUpdates(userId, onUpdate) {
    return supabase
        .channel('service_requests_changes')
        .on('postgres_changes', {
            event: 'UPDATE',
            schema: 'public',
            table: 'service_requests',
            filter: `user_id=eq.${userId}`
        }, (payload) => {
            if (payload.new.payment_status === 'paid' || payload.new.status === 'completed') {
                onUpdate(payload.new);
            }
        })
        .subscribe();
}

// Generate valuation result (called by backend via Edge Function)
async function generateValuationResult(serviceId) {
    const { data: service } = await supabase
        .from('service_requests')
        .select('*')
        .eq('id', serviceId)
        .single();
    
    const currentYear = new Date().getFullYear();
    const age = currentYear - service.year;
    const baseValue = 2000000;
    let marketValue = Math.max(300000, baseValue - (baseValue * age * 0.1));
    
    if (service.make?.toLowerCase() === 'toyota') marketValue *= 1.1;
    if (service.make?.toLowerCase() === 'mercedes') marketValue *= 1.2;
    if (service.make?.toLowerCase() === 'bmw') marketValue *= 1.15;
    
    const result = {
        market_value: Math.round(marketValue),
        age_years: age,
        depreciation_rate: age * 10,
        certificate_number: `AUTO-VAL-${service.id.substring(0, 8)}`,
        valuation_date: new Date().toISOString()
    };
    
    await supabase
        .from('service_requests')
        .update({
            result: result,
            status: 'completed'
        })
        .eq('id', serviceId);
    
    return result;
}

// Generate inspection result
async function generateInspectionResult(serviceId) {
    const { data: service } = await supabase
        .from('service_requests')
        .select('*')
        .eq('id', serviceId)
        .single();
    
    const score = Math.floor(Math.random() * 25) + 75;
    const result = {
        overall_score: score,
        verdict: score >= 85 ? 'Excellent' : (score >= 70 ? 'Good' : 'Fair'),
        certificate_number: `AUTO-INS-${service.id.substring(0, 8)}`,
        inspection_date: new Date().toISOString(),
        categories: {
            engine: score >= 80 ? 'Good' : 'Needs Attention',
            transmission: score >= 75 ? 'Good' : 'Check Required',
            brakes: score >= 85 ? 'Excellent' : 'Service Recommended',
            electrical: score >= 80 ? 'Working' : 'Inspect Further'
        }
    };
    
    await supabase
        .from('service_requests')
        .update({
            result: result,
            status: 'completed'
        })
        .eq('id', serviceId);
    
    return result;
}

window.autoV = {
    supabase,
    requireAuth,
    logout,
    createServiceRequest,
    getServiceRequests,
    loadFees,
    initiatePayment,
    checkPaymentStatus,
    subscribeToServiceUpdates,
    generateValuationResult,
    generateInspectionResult
};
