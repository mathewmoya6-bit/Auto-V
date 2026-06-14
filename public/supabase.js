// supabase.js - Single Source of Truth
// This file should be loaded FIRST before dashboard.html

// Check if already initialized to prevent duplicate errors
if (typeof window.autoV === 'undefined') {
    
    const SUPABASE_URL = "https://tsvejnzxrxrrecgquxbq.supabase.co";
    const SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRzdmVqbnp4cnhycmVjZ3F1eGJxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODExODczNjgsImV4cCI6MjA5Njc2MzM2OH0.PCEppwafuPatBoWh4OnhzgHv6fA9uF5-bWW9mmf2VoQ";
    
    // Create supabase client only once
    window._supabaseClient = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
    
    // M-PESA PRODUCTION CREDENTIALS
    window.MPESA_CONFIG = {
        consumerKey: "LI2gcJZEheN8qCfXHEXV4gdYXvOBHVnv",
        consumerSecret: "aGGo8AuPJVpsZLcs",
        passkey: "7eb17a031bdfd5b4251863a1ddb72c5b9cd14f3385aa6a258c1442a0116e8277",
        shortcode: "4095377",
        callbackUrl: "https://tsvejnzxrxrrecgquxbq.supabase.co/functions/v1/mpesa-callback"
    };
    
    let realtimeChannel = null;
    
    // ============================================
    // AUTHENTICATION
    // ============================================
    window.requireAuth = async function() {
        const { data: { session }, error } = await window._supabaseClient.auth.getSession();
        if (error || !session) {
            window.location.href = "login.html";
            return null;
        }
        return session.user;
    };
    
    window.logout = async function() {
        if (realtimeChannel) await window._supabaseClient.removeChannel(realtimeChannel);
        await window._supabaseClient.auth.signOut();
        window.location.href = "login.html";
    };
    
    // ============================================
    // SERVICE REQUESTS
    // ============================================
    window.createServiceRequest = async function(data) {
        const { data: request, error } = await window._supabaseClient
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
    };
    
    window.getServiceRequests = async function(userId, limit = 50) {
        const { data, error } = await window._supabaseClient
            .from('service_requests')
            .select('*')
            .eq('user_id', userId)
            .order('created_at', { ascending: false })
            .limit(limit);
        
        if (error) throw error;
        return data || [];
    };
    
    window.getServiceRequestById = async function(id) {
        const { data, error } = await window._supabaseClient
            .from('service_requests')
            .select('*')
            .eq('id', id)
            .single();
        
        if (error) throw error;
        return data;
    };
    
    // ============================================
    // FEES MANAGEMENT
    // ============================================
    window.loadFees = async function() {
        try {
            const { data: valuationFee } = await window._supabaseClient
                .from('system_settings')
                .select('setting_value')
                .eq('setting_key', 'valuation_fee')
                .single();
            
            const { data: inspectionFee } = await window._supabaseClient
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
    };
    
    // ============================================
    // REAL M-PESA INTEGRATION
    // ============================================
    window.getMpesaAccessToken = async function() {
        const auth = btoa(`${window.MPESA_CONFIG.consumerKey}:${window.MPESA_CONFIG.consumerSecret}`);
        const response = await fetch('https://api.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials', {
            method: 'GET',
            headers: { 'Authorization': `Basic ${auth}` }
        });
        const data = await response.json();
        return data.access_token;
    };
    
    window.initiateMpesaStkPush = async function(phoneNumber, amount, accountReference, transactionDesc) {
        try {
            const accessToken = await window.getMpesaAccessToken();
            const timestamp = new Date().toISOString().replace(/[^0-9]/g, '').slice(0, 14);
            const password = btoa(`${window.MPESA_CONFIG.shortcode}${window.MPESA_CONFIG.passkey}${timestamp}`);
            
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
                    BusinessShortCode: window.MPESA_CONFIG.shortcode,
                    Password: password,
                    Timestamp: timestamp,
                    TransactionType: 'CustomerPayBillOnline',
                    Amount: amount,
                    PartyA: formattedPhone,
                    PartyB: window.MPESA_CONFIG.shortcode,
                    PhoneNumber: formattedPhone,
                    CallBackURL: window.MPESA_CONFIG.callbackUrl,
                    AccountReference: accountReference.substring(0, 12),
                    TransactionDesc: transactionDesc.substring(0, 13)
                })
            });
            
            return await response.json();
        } catch (error) {
            console.error('M-Pesa Error:', error);
            return { ResponseCode: '1', ResponseDescription: error.message };
        }
    };
    
    window.initiatePayment = async function(serviceId, amount, phone, reference, serviceType) {
        const shortId = serviceId ? serviceId.toString().substring(0, 8) : Date.now().toString().substring(0, 8);
        const accountRef = `${serviceType === 'valuation' ? 'VAL' : 'INS'}${shortId}`;
        
        const result = await window.initiateMpesaStkPush(phone, amount, accountRef, `AUTO-V ${serviceType}`);
        
        if (result.ResponseCode === '0') {
            await window._supabaseClient
                .from('service_requests')
                .update({ mpesa_checkout_request_id: result.CheckoutRequestID })
                .eq('id', serviceId);
        }
        
        return result;
    };
    
    window.checkPaymentStatus = async function(serviceId) {
        const { data, error } = await window._supabaseClient
            .from('service_requests')
            .select('payment_status, status, result')
            .eq('id', serviceId)
            .single();
        
        if (error) return { payment_status: 'pending', status: 'pending' };
        return data;
    };
    
    // ============================================
    // REALTIME SUBSCRIPTIONS
    // ============================================
    window.subscribeToServiceUpdates = function(userId, onUpdate) {
        if (realtimeChannel) window._supabaseClient.removeChannel(realtimeChannel);
        
        realtimeChannel = window._supabaseClient
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
    };
    
    // Export all functions
    window.autoV = {
        supabase: window._supabaseClient,
        MPESA_CONFIG: window.MPESA_CONFIG,
        requireAuth: window.requireAuth,
        logout: window.logout,
        createServiceRequest: window.createServiceRequest,
        getServiceRequests: window.getServiceRequests,
        getServiceRequestById: window.getServiceRequestById,
        loadFees: window.loadFees,
        initiatePayment: window.initiatePayment,
        checkPaymentStatus: window.checkPaymentStatus,
        subscribeToServiceUpdates: window.subscribeToServiceUpdates
    };
    
    console.log('✅ AUTO-V System Ready | M-Pesa Live | Paybill: 4095377');
}
