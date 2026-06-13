// api/payment.js - Vercel Serverless Function
const axios = require('axios');

// M-Pesa API Configuration
const CONSUMER_KEY = process.env.MPESA_CONSUMER_KEY || "LI2gcJZEheN8qCfXHEXV4gdYXvOBHVnv";
const CONSUMER_SECRET = process.env.MPESA_CONSUMER_SECRET || "aGGo8AuPJVpsZLcs";
const PASSKEY = process.env.MPESA_PASSKEY || "7eb17a031bdfd5b4251863a1ddb72c5b9cd14f3385aa6a258c1442a0116e8277";
const SHORTCODE = process.env.MPESA_SHORTCODE || "4095377";
const ENVIRONMENT = 'production'; // 'sandbox' or 'production'

// Get OAuth Token
async function getAccessToken() {
    const auth = Buffer.from(`${CONSUMER_KEY}:${CONSUMER_SECRET}`).toString('base64');
    
    try {
        const response = await axios.get(
            ENVIRONMENT === 'production' 
                ? 'https://api.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials'
                : 'https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials',
            {
                headers: {
                    Authorization: `Basic ${auth}`
                }
            }
        );
        return response.data.access_token;
    } catch (error) {
        console.error('Error getting access token:', error.response?.data || error.message);
        throw error;
    }
}

// Generate Password for STK Push
function generatePassword() {
    const timestamp = getTimestamp();
    const password = Buffer.from(`${SHORTCODE}${PASSKEY}${timestamp}`).toString('base64');
    return { password, timestamp };
}

function getTimestamp() {
    const date = new Date();
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    const seconds = String(date.getSeconds()).padStart(2, '0');
    return `${year}${month}${day}${hours}${minutes}${seconds}`;
}

// STK Push (Lipa Na M-Pesa Online)
async function stkPush(phoneNumber, amount, accountReference, transactionDesc) {
    const token = await getAccessToken();
    const { password, timestamp } = generatePassword();
    
    // Format phone number (remove 0 or +254, add 254)
    let formattedPhone = phoneNumber.toString().replace(/\s/g, '');
    if (formattedPhone.startsWith('0')) {
        formattedPhone = '254' + formattedPhone.substring(1);
    } else if (formattedPhone.startsWith('+')) {
        formattedPhone = formattedPhone.substring(1);
    }
    
    const data = {
        BusinessShortCode: SHORTCODE,
        Password: password,
        Timestamp: timestamp,
        TransactionType: 'CustomerPayBillOnline',
        Amount: amount,
        PartyA: formattedPhone,
        PartyB: SHORTCODE,
        PhoneNumber: formattedPhone,
        CallBackURL: `${process.env.VERCEL_URL || 'https://autov.vercel.app'}/api/callback`,
        AccountReference: accountReference,
        TransactionDesc: transactionDesc
    };
    
    try {
        const response = await axios.post(
            ENVIRONMENT === 'production'
                ? 'https://api.safaricom.co.ke/mpesa/stkpush/v1/processrequest'
                : 'https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest',
            data,
            {
                headers: {
                    Authorization: `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            }
        );
        return response.data;
    } catch (error) {
        console.error('STK Push error:', error.response?.data || error.message);
        throw error;
    }
}

// Query STK Push Status
async function queryStatus(checkoutRequestID) {
    const token = await getAccessToken();
    const { password, timestamp } = generatePassword();
    
    const data = {
        BusinessShortCode: SHORTCODE,
        Password: password,
        Timestamp: timestamp,
        CheckoutRequestID: checkoutRequestID
    };
    
    try {
        const response = await axios.post(
            ENVIRONMENT === 'production'
                ? 'https://api.safaricom.co.ke/mpesa/stkpushquery/v1/query'
                : 'https://sandbox.safaricom.co.ke/mpesa/stkpushquery/v1/query',
            data,
            {
                headers: {
                    Authorization: `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            }
        );
        return response.data;
    } catch (error) {
        console.error('Query status error:', error.response?.data || error.message);
        throw error;
    }
}

// Vercel API Handler
module.exports = async (req, res) => {
    // Enable CORS
    res.setHeader('Access-Control-Allow-Credentials', true);
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET,OPTIONS,PATCH,DELETE,POST,PUT');
    res.setHeader('Access-Control-Allow-Headers', 'X-CSRF-Token, X-Requested-With, Accept, Accept-Version, Content-Length, Content-MD5, Content-Type, Date, X-Api-Version');
    
    if (req.method === 'OPTIONS') {
        res.status(200).end();
        return;
    }
    
    const { action } = req.query;
    
    try {
        if (action === 'stkpush') {
            const { phone, amount, reference, description } = req.body;
            const result = await stkPush(phone, amount, reference, description);
            res.status(200).json(result);
        } 
        else if (action === 'query') {
            const { checkoutRequestID } = req.body;
            const result = await queryStatus(checkoutRequestID);
            res.status(200).json(result);
        }
        else {
            res.status(400).json({ error: 'Invalid action' });
        }
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
};
