// services/mpesa-callback/index.ts - M-Pesa Callback Handler (FastAPI Backend)

import { Request, Response } from 'express';

// ─── Types ──────────────────────────────────────────────────────

interface MpesaCallbackMetadata {
  Item: Array<{
    Name: string;
    Value: string | number;
  }>;
}

interface MpesaStkCallback {
  MerchantRequestID: string;
  CheckoutRequestID: string;
  ResultCode: string | number;
  ResultDesc: string;
  CallbackMetadata?: MpesaCallbackMetadata;
}

interface MpesaCallbackBody {
  Body: {
    stkCallback: MpesaStkCallback;
  };
}

interface PaymentRecord {
  id: string;
  payment_id: string;
  user_id?: string;
  amount: number;
  status: string;
  checkout_request_id?: string;
  mpesa_code?: string;
  transaction_id?: string;
  metadata?: Record<string, any>;
  [key: string]: any;
}

interface CallbackResponse {
  ResultCode: number;
  ResultDesc: string;
}

// ─── Configuration ────────────────────────────────────────────

const API_BASE = process.env.API_BASE_URL || 'http://localhost:8000/api';
const MPESA_SHORTCODE = process.env.MPESA_SHORTCODE || '4095377';
const MPESA_CALLBACK_URL = process.env.MPESA_CALLBACK_URL || '';
const MPESA_ENV = process.env.MPESA_ENV || 'production';
const API_TOKEN = process.env.API_INTERNAL_TOKEN || ''; // Internal token for service-to-service auth

// ─── Logger ──────────────────────────────────────────────────

const logger = {
  info: (message: string, meta?: any) => {
    console.log(JSON.stringify({
      timestamp: new Date().toISOString(),
      level: 'INFO',
      message,
      service: 'mpesa-callback',
      ...meta
    }));
  },
  error: (message: string, meta?: any) => {
    console.error(JSON.stringify({
      timestamp: new Date().toISOString(),
      level: 'ERROR',
      message,
      service: 'mpesa-callback',
      ...meta
    }));
  },
  warn: (message: string, meta?: any) => {
    console.warn(JSON.stringify({
      timestamp: new Date().toISOString(),
      level: 'WARN',
      message,
      service: 'mpesa-callback',
      ...meta
    }));
  },
  debug: (message: string, meta?: any) => {
    if (process.env.DEBUG === 'true') {
      console.debug(JSON.stringify({
        timestamp: new Date().toISOString(),
        level: 'DEBUG',
        message,
        service: 'mpesa-callback',
        ...meta
      }));
    }
  }
};

// ─── API Client ──────────────────────────────────────────────────

async function apiRequest(
  endpoint: string,
  method: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE' = 'GET',
  body?: any
): Promise<any> {
  const url = endpoint.startsWith('http') ? endpoint : `${API_BASE}${endpoint}`;
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
  };

  // Use internal token for service-to-service auth
  if (API_TOKEN) {
    headers['Authorization'] = `Bearer ${API_TOKEN}`;
    headers['X-Internal-Request'] = 'true';
  }

  const options: RequestInit = {
    method,
    headers,
    ...(body && { body: JSON.stringify(body) })
  };

  try {
    const response = await fetch(url, options);
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || data.error || `HTTP ${response.status}`);
    }

    return data;
  } catch (error) {
    logger.error('API request failed', {
      endpoint,
      method,
      error: error instanceof Error ? error.message : String(error)
    });
    throw error;
  }
}

// ─── Main Callback Handler ──────────────────────────────────

export async function handleMpesaCallback(
  callbackData: MpesaCallbackBody
): Promise<CallbackResponse> {
  const startTime = Date.now();

  try {
    logger.info('📞 M-Pesa Callback Received', {
      timestamp: new Date().toISOString(),
      hasBody: !!callbackData?.Body
    });

    // ─── Validate Callback Data ──────────────────────────────

    if (!callbackData || !callbackData.Body) {
      logger.error('❌ Invalid callback data: Missing Body');
      return { ResultCode: 1, ResultDesc: 'Invalid callback data' };
    }

    const stkCallback = callbackData.Body.stkCallback;

    if (!stkCallback) {
      logger.error('❌ Missing stkCallback in payload');
      return { ResultCode: 1, ResultDesc: 'Missing stkCallback' };
    }

    // ─── Extract Callback Values ─────────────────────────────

    const {
      MerchantRequestID,
      CheckoutRequestID,
      ResultCode,
      ResultDesc,
      CallbackMetadata
    } = stkCallback;

    logger.info('📊 Callback Details', {
      MerchantRequestID,
      CheckoutRequestID,
      ResultCode,
      ResultDesc
    });

    if (!CheckoutRequestID) {
      logger.error('❌ Missing CheckoutRequestID');
      return { ResultCode: 1, ResultDesc: 'Missing CheckoutRequestID' };
    }

    // ─── Extract Transaction Details ──────────────────────────

    let transactionId: string | null = null;
    let amount: number | null = null;
    let phone: string | null = null;
    let transactionDate: string | null = null;

    if (CallbackMetadata && CallbackMetadata.Item) {
      for (const item of CallbackMetadata.Item) {
        const { Name, Value } = item;
        switch (Name) {
          case 'MpesaReceiptNumber':
            transactionId = String(Value);
            logger.info(`✅ Receipt Number: ${transactionId}`);
            break;
          case 'Amount':
            amount = typeof Value === 'number' ? Value : parseFloat(String(Value));
            logger.info(`💰 Amount: ${amount}`);
            break;
          case 'PhoneNumber':
            phone = String(Value);
            logger.info(`📱 Phone: ${phone}`);
            break;
          case 'TransactionDate':
            transactionDate = String(Value);
            logger.info(`📅 Transaction Date: ${transactionDate}`);
            break;
        }
      }
    } else {
      logger.warn('⚠️ No CallbackMetadata found');
    }

    // ─── Find Payment via API ──────────────────────────────────

    try {
      logger.info('🔍 Looking up payment by CheckoutRequestID', { CheckoutRequestID });

      const payment = await apiRequest(
        `/payments/checkout/${CheckoutRequestID}`,
        'GET'
      );

      if (!payment) {
        logger.error('❌ Payment not found', { CheckoutRequestID });
        return { ResultCode: 1, ResultDesc: 'Payment not found' };
      }

      const paymentId = payment.payment_id || payment.id;
      const paymentUuid = payment.id;
      const currentStatus = payment.status;

      logger.info(`✅ Found payment: ${paymentId} (UUID: ${paymentUuid})`, {
        currentStatus,
        amount: payment.amount
      });

      // ─── Check if Already Processed ─────────────────────────

      if (currentStatus === 'completed') {
        logger.info(`ℹ️ Payment ${paymentId} already completed`);
        return { ResultCode: 0, ResultDesc: 'Already processed' };
      }

      // ─── Process Based on Result Code ──────────────────────

      const resultCodeStr = String(ResultCode);

      // ✅ SUCCESSFUL PAYMENT
      if (resultCodeStr === '0' && transactionId) {
        logger.info(`✅ Payment successful: ${transactionId}`);

        const updateData: Partial<PaymentRecord> = {
          status: 'completed',
          mpesa_code: transactionId,
          transaction_id: transactionId,
          mpesa_result_code: resultCodeStr,
          mpesa_result_desc: ResultDesc || 'Transaction completed',
          paid_at: new Date().toISOString()
        };

        if (amount) {
          updateData.amount = amount;
        }
        if (phone) {
          updateData.mpesa_phone = phone;
        }

        // Update via API
        await apiRequest(
          `/payments/${paymentUuid}`,
          'PATCH',
          updateData
        );

        logger.info(`✅ Payment ${paymentId} completed successfully`, {
          receipt: transactionId,
          amount
        });

        // ─── Trigger Post-Payment Actions ─────────────────────
        await triggerPostPaymentActions(paymentUuid, paymentId);

        return { ResultCode: 0, ResultDesc: 'Success' };
      }

      // ⏸️ CANCELLED PAYMENT (User cancelled or timeout)
      else if (['1037', '1032'].includes(resultCodeStr)) {
        logger.warn(`⚠️ Payment cancelled: ${ResultDesc}`);

        await apiRequest(
          `/payments/${paymentUuid}`,
          'PATCH',
          {
            status: 'cancelled',
            mpesa_result_code: resultCodeStr,
            mpesa_result_desc: ResultDesc || 'Transaction cancelled'
          }
        );

        return { ResultCode: 0, ResultDesc: 'Success' };
      }

      // ❌ FAILED PAYMENT
      else {
        logger.error(`❌ Payment failed: ${ResultDesc}`);

        await apiRequest(
          `/payments/${paymentUuid}`,
          'PATCH',
          {
            status: 'failed',
            mpesa_result_code: resultCodeStr,
            mpesa_result_desc: ResultDesc || 'Transaction failed'
          }
        );

        return { ResultCode: 0, ResultDesc: 'Success' };
      }

    } catch (dbError) {
      logger.error('❌ API error', {
        error: dbError instanceof Error ? dbError.message : String(dbError)
      });
      return { ResultCode: 1, ResultDesc: 'API error' };
    }

  } catch (error) {
    const duration = Date.now() - startTime;
    logger.error('❌ Callback handler error', {
      error: error instanceof Error ? error.message : String(error),
      stack: error instanceof Error ? error.stack : undefined,
      durationMs: duration
    });
    return { ResultCode: 1, ResultDesc: 'System error' };
  }
}

// ─── Post-Payment Actions ────────────────────────────────────

async function triggerPostPaymentActions(
  paymentUuid: string,
  paymentId: string
): Promise<void> {
  try {
    logger.info(`🎉 Post-payment actions triggered for ${paymentId}`);

    // Get full payment details
    const payment = await apiRequest(`/payments/${paymentUuid}`, 'GET');

    if (!payment) {
      logger.warn(`⚠️ Payment ${paymentId} not found for post-actions`);
      return;
    }

    // ─── 1. Send Confirmation ────────────────────────────────
    try {
      await sendPaymentConfirmation(payment);
    } catch (e) {
      logger.error('❌ Failed to send confirmation', {
        paymentId,
        error: e instanceof Error ? e.message : String(e)
      });
    }

    // ─── 2. Create Service Request ───────────────────────────
    try {
      await createServiceRequestFromPayment(payment);
    } catch (e) {
      logger.error('❌ Failed to create service request', {
        paymentId,
        error: e instanceof Error ? e.message : String(e)
      });
    }

    // ─── 3. Trigger Webhook ──────────────────────────────────
    try {
      await triggerWebhook(payment);
    } catch (e) {
      logger.error('❌ Failed to trigger webhook', {
        paymentId,
        error: e instanceof Error ? e.message : String(e)
      });
    }

    // ─── 4. Update Payment Metadata ──────────────────────────
    await apiRequest(
      `/payments/${paymentUuid}`,
      'PATCH',
      {
        metadata: {
          ...payment.metadata,
          post_payment_processed: true,
          post_payment_at: new Date().toISOString()
        }
      }
    );

    logger.info(`✅ Post-payment actions completed for ${paymentId}`);

  } catch (error) {
    logger.error('❌ Post-payment actions error', {
      paymentId,
      error: error instanceof Error ? error.message : String(error)
    });
  }
}

// ─── Send Payment Confirmation ──────────────────────────────

async function sendPaymentConfirmation(payment: PaymentRecord): Promise<void> {
  logger.info(`📧 Sending confirmation for payment ${payment.payment_id}`);

  // Call backend notification service
  try {
    await apiRequest(
      '/notifications/payment-confirmation',
      'POST',
      {
        payment_id: payment.payment_id,
        user_id: payment.user_id,
        email: payment.metadata?.email,
        amount: payment.amount,
        receipt: payment.mpesa_code,
        service: payment.metadata?.service || 'AUTO-V Service'
      }
    );
    logger.info('✅ Confirmation notification sent');
  } catch (error) {
    logger.error('❌ Failed to send confirmation', {
      error: error instanceof Error ? error.message : String(error)
    });
  }
}

// ─── Create Service Request ──────────────────────────────────

async function createServiceRequestFromPayment(
  payment: PaymentRecord
): Promise<void> {
  logger.info(`📝 Creating service request for payment ${payment.payment_id}`);

  const serviceData = {
    user_id: payment.user_id,
    service_type: payment.metadata?.service || 'unknown',
    purpose: payment.metadata?.purpose,
    status: 'paid',
    payment_id: payment.payment_id,
    payment_reference: payment.payment_id,
    reference: payment.metadata?.reference,
    amount: payment.amount
  };

  try {
    const result = await apiRequest(
      '/service-requests',
      'POST',
      serviceData
    );
    logger.info(`✅ Service request created: ${result.id}`);
  } catch (error) {
    logger.error('❌ Failed to create service request', {
      paymentId: payment.payment_id,
      error: error instanceof Error ? error.message : String(error)
    });
    throw error;
  }
}

// ─── Trigger Webhook ──────────────────────────────────────────

async function triggerWebhook(payment: PaymentRecord): Promise<void> {
  const webhookUrl = process.env.PAYMENT_WEBHOOK_URL;

  if (!webhookUrl) {
    logger.debug('ℹ️ No webhook URL configured');
    return;
  }

  const payload = {
    event: 'payment.completed',
    payment_id: payment.payment_id,
    amount: payment.amount,
    mpesa_code: payment.mpesa_code,
    user_id: payment.user_id,
    timestamp: new Date().toISOString(),
    metadata: payment.metadata
  };

  try {
    const response = await fetch(webhookUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Payment-ID': payment.payment_id || '',
        'X-Webhook-Source': 'auto-v-mpesa'
      },
      body: JSON.stringify(payload)
    });

    if (!response.ok) {
      logger.warn(`⚠️ Webhook returned ${response.status}`, {
        status: response.status,
        statusText: response.statusText
      });
    } else {
      logger.info('✅ Webhook triggered successfully');
    }
  } catch (error) {
    logger.error('❌ Webhook failed', {
      error: error instanceof Error ? error.message : String(error)
    });
    // Don't throw - webhook failure shouldn't break the flow
  }
}

// ─── Supplementary Functions ────────────────────────────────

export async function handleMpesaTimeout(
  checkoutId: string
): Promise<{ success: boolean; status?: string; error?: string }> {
  try {
    const payment = await apiRequest(
      `/payments/checkout/${checkoutId}`,
      'GET'
    );

    if (!payment) {
      return { success: false, error: 'Payment not found' };
    }

    if (payment.status === 'pending') {
      await apiRequest(
        `/payments/${payment.id}`,
        'PATCH',
        {
          status: 'timeout',
          mpesa_result_code: '1037',
          mpesa_result_desc: 'Transaction timed out'
        }
      );

      logger.info(`⏰ Payment ${payment.payment_id} marked as timeout`);
      return { success: true, status: 'timeout' };
    }

    return { success: true, status: payment.status };
  } catch (error) {
    logger.error('❌ Timeout handler error', {
      error: error instanceof Error ? error.message : String(error)
    });
    return { success: false, error: String(error) };
  }
}

export async function verifyMpesaTransaction(
  checkoutId: string
): Promise<{
  verified: boolean;
  status?: string;
  payment_id?: string;
  mpesa_code?: string;
  error?: string;
}> {
  try {
    const payment = await apiRequest(
      `/payments/checkout/${checkoutId}`,
      'GET'
    );

    if (!payment) {
      return { verified: false, error: 'Payment not found' };
    }

    return {
      verified: true,
      status: payment.status,
      payment_id: payment.payment_id,
      mpesa_code: payment.mpesa_code
    };
  } catch (error) {
    logger.error('❌ Verification error', {
      error: error instanceof Error ? error.message : String(error)
    });
    return { verified: false, error: String(error) };
  }
}

// ─── Express Route Handler (for API route) ──────────────────

export async function mpesaCallbackHandler(
  req: Request,
  res: Response
): Promise<void> {
  try {
    const callbackData = req.body;

    if (!callbackData) {
      res.status(200).json({ ResultCode: 1, ResultDesc: 'No data' });
      return;
    }

    logger.info('📞 M-Pesa callback received');

    const result = await handleMpesaCallback(callbackData);

    // Always return 200 OK to Safaricom
    res.status(200).json(result);
  } catch (error) {
    logger.error('❌ Callback route error', {
      error: error instanceof Error ? error.message : String(error)
    });
    res.status(200).json({ ResultCode: 1, ResultDesc: 'System error' });
  }
}

// ─── FastAPI Route Handler (Alternative) ──────────────────

// If you're using FastAPI directly instead of Express:
/*
from fastapi import FastAPI, Request, Response
from pydantic import BaseModel

app = FastAPI()

class MpesaCallbackBody(BaseModel):
    Body: dict

@app.post("/api/mpesa/callback")
async def handle_mpesa_callback(request: Request, body: MpesaCallbackBody):
    # Convert to JSON and call handleMpesaCallback
    result = await handleMpesaCallback(body.dict())
    return result
*/

// ─── Exports ──────────────────────────────────────────────────

export default {
  handleMpesaCallback,
  handleMpesaTimeout,
  verifyMpesaTransaction,
  mpesaCallbackHandler
};
