// api/callback.js - M-Pesa Callback URL
const { createClient } = require('@supabase/supabase-js');

const supabase = createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL,
    process.env.SUPABASE_SERVICE_ROLE_KEY
);

module.exports = async (req, res) => {
    console.log('Callback received:', JSON.stringify(req.body, null, 2));
    
    const { Body } = req.body;
    
    if (Body && Body.stkCallback) {
        const {
            MerchantRequestID,
            CheckoutRequestID,
            ResultCode,
            ResultDesc,
            CallbackMetadata
        } = Body.stkCallback;
        
        // Save payment record to Supabase
        const paymentRecord = {
            merchant_request_id: MerchantRequestID,
            checkout_request_id: CheckoutRequestID,
            result_code: ResultCode,
            result_description: ResultDesc,
            amount: CallbackMetadata?.Item?.find(i => i.Name === 'Amount')?.Value,
            mpesa_receipt_number: CallbackMetadata?.Item?.find(i => i.Name === 'MpesaReceiptNumber')?.Value,
            transaction_date: CallbackMetadata?.Item?.find(i => i.Name === 'TransactionDate')?.Value,
            phone_number: CallbackMetadata?.Item?.find(i => i.Name === 'PhoneNumber')?.Value,
            status: ResultCode === 0 ? 'completed' : 'failed',
            created_at: new Date().toISOString()
        };
        
        await supabase.from('payments').insert([paymentRecord]);
        
        // Update related valuation/inspection if needed
        if (ResultCode === 0) {
            // Payment successful - update record
            console.log('Payment successful:', MpesaReceiptNumber);
        }
    }
    
    res.status(200).json({ ResultCode: 0, ResultDesc: 'Success' });
};
