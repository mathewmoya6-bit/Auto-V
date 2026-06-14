// supabase.js - Single Source of Truth
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
let realtimeChannel = null;

// ============================================
// AUTHENTICATION
// ============================================
async function requireAuth() {
    const { data: { session }, error } = await supabase.auth.getSession();
    if (error || !session) {
        window.location.href = "login.html";
        return null;
    }
    return session.user;
}

async function logout() {
    if (realtimeChannel) await supabase.removeChannel(realtimeChannel);
    await supabase.auth.signOut();
    window.location.href = "login.html";
}

// ============================================
// SERVICE REQUESTS
// ============================================
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
            purpose: data.purpose || null,
            mileage: data.mileage || null,
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

async function getServiceRequests(userId, limit = 50) {
    const { data, error } = await supabase
        .from('service_requests')
        .select('*')
        .eq('user_id', userId)
        .order('created_at', { ascending: false })
        .limit(limit);
    
    if (error) throw error;
    return data || [];
}

async function getServiceRequestById(id) {
    const { data, error } = await supabase
        .from('service_requests')
        .select('*')
        .eq('id', id)
        .single();
    
    if (error) throw error;
    return data;
}

// ============================================
// FEES MANAGEMENT
// ============================================
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

// ============================================
// REAL M-PESA INTEGRATION
// ============================================
async function getMpesaAccessToken() {
    const auth = btoa(`${MPESA_CONFIG.consumerKey}:${MPESA_CONFIG.consumerSecret}`);
    const response = await fetch('https://api.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials', {
        method: 'GET',
        headers: { 'Authorization': `Basic ${auth}` }
    });
    const data = await response.json();
    return data.access_token;
}

async function initiateMpesaStkPush(phoneNumber, amount, accountReference, transactionDesc) {
    try {
        const accessToken = await getMpesaAccessToken();
        const timestamp = new Date().toISOString().replace(/[^0-9]/g, '').slice(0, 14);
        const password = btoa(`${MPESA_CONFIG.shortcode}${MPESA_CONFIG.passkey}${timestamp}`);
        
        let formattedPhone = phoneNumber.replace(/\D/g, '');
        if (formattedPhone.startsWith('0')) formattedPhone = '254' + formattedPhone.substring(1);
        if (!formattedPhone.startsWith('254')) formattedPhone = '254' + formattedPhone;
        
        const response = await fetch('https://api.safaricom.co.ke/mpesa/stkpush/v1/processrequest', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${accessToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
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
            })
        });
        
        return await response.json();
    } catch (error) {
        console.error('M-Pesa Error:', error);
        return { ResponseCode: '1', ResponseDescription: error.message };
    }
}

async function initiatePayment(serviceId, amount, phone, reference, serviceType) {
    const shortId = serviceId ? serviceId.toString().substring(0, 8) : Date.now().toString().substring(0, 8);
    const accountRef = `${serviceType === 'valuation' ? 'VAL' : 'INS'}${shortId}`;
    
    const result = await initiateMpesaStkPush(phone, amount, accountRef, `AUTO-V ${serviceType}`);
    
    if (result.ResponseCode === '0') {
        await supabase
            .from('service_requests')
            .update({ mpesa_checkout_request_id: result.CheckoutRequestID })
            .eq('id', serviceId);
    }
    
    return result;
}

async function checkPaymentStatus(serviceId) {
    const { data, error } = await supabase
        .from('service_requests')
        .select('payment_status, status, result')
        .eq('id', serviceId)
        .single();
    
    if (error) return { payment_status: 'pending', status: 'pending' };
    return data;
}

// ============================================
// REALTIME SUBSCRIPTIONS
// ============================================
function subscribeToServiceUpdates(userId, onUpdate) {
    if (realtimeChannel) supabase.removeChannel(realtimeChannel);
    
    realtimeChannel = supabase
        .channel(`service_updates_${userId}`)
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
    
    return realtimeChannel;
}

// ============================================
// EXPORTS
// ============================================
window.autoV = {
    supabase,
    MPESA_CONFIG,
    requireAuth,
    logout,
    createServiceRequest,
    getServiceRequests,
    getServiceRequestById,
    loadFees,
    initiatePayment,
    checkPaymentStatus,
    subscribeToServiceUpdates
};

console.log('✅ AUTO-V System Ready | M-Pesa Live | Paybill: 4095377');
