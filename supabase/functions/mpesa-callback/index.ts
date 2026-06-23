// services/mpesa-callback/index.ts - M-Pesa Callback Handler (Production Ready)

import { supabase } from '../supabase-client';
import { createClient } from '@supabase/supabase-js';

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
  metadata?: Record<string, any>;
  [key: string]: any;
}

interface CallbackResponse {
  ResultCode: number;
  ResultDesc: string;
}

// ─── Configuration ────────────────────────────────────────────

const MPESA_SHORTCODE = process.env.MPESA_SHORTCODE || '4095377';
const MPESA_CALLBACK_URL = process.env.MPESA_CALLBACK_URL || '';
const MPESA_ENV = process.env.MPESA_ENV || 'production';

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

    // ─── Find Payment in Database ─────────────────────────────

    try {
      logger.info('🔍 Looking up payment by CheckoutRequestID', { CheckoutRequestID });

      const { data: payment, error: findError } = await supabase
        .from('payments')
        .select('*')
        .eq('checkout_request_id', CheckoutRequestID)
        .single();

      if (findError || !payment) {
        logger.error('❌ Payment not found', {
          CheckoutRequestID,
          error: findError?.message
        });
        return { ResultCode: 1, ResultDesc: 'Payment not found' };
      }

      const paymentId = payment.payment_id;
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
          paid_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        };

        if (amount) {
          updateData.amount = amount;
        }
        if (phone) {
          updateData.mpesa_phone = phone;
        }

        const { error: updateError } = await supabase
          .from('payments')
          .update(updateData)
          .eq('id', paymentUuid);

        if (updateError) {
          logger.error('❌ Database update failed', {
            paymentId,
            error: updateError.message
          });
          return { ResultCode: 1, ResultDesc: 'Update failed' };
        }

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

        const { error: updateError } = await supabase
          .from('payments')
          .update({
            status: 'cancelled',
            mpesa_result_code: resultCodeStr,
            mpesa_result_desc: ResultDesc || 'Transaction cancelled',
            updated_at: new Date().toISOString()
          })
          .eq('id', paymentUuid);

        if (updateError) {
          logger.error('❌ Database update failed', {
            paymentId,
            error: updateError.message
          });
          return { ResultCode: 1, ResultDesc: 'Update failed' };
        }

        return { ResultCode: 0, ResultDesc: 'Success' };
      }

      // ❌ FAILED PAYMENT
      else {
        logger.error(`❌ Payment failed: ${ResultDesc}`);

        const { error: updateError } = await supabase
          .from('payments')
          .update({
            status: 'failed',
            mpesa_result_code: resultCodeStr,
            mpesa_result_desc: ResultDesc || 'Transaction failed',
            updated_at: new Date().toISOString()
          })
          .eq('id', paymentUuid);

        if (updateError) {
          logger.error('❌ Database update failed', {
            paymentId,
            error: updateError.message
          });
          return { ResultCode: 1, ResultDesc: 'Update failed' };
        }

        return { ResultCode: 0, ResultDesc: 'Success' };
      }

    } catch (dbError) {
      logger.error('❌ Database error', {
        error: dbError instanceof Error ? dbError.message : String(dbError)
      });
      return { ResultCode: 1, ResultDesc: 'Database error' };
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
    const { data: payment, error } = await supabase
      .from('payments')
      .select('*')
      .eq('id', paymentUuid)
      .single();

    if (error || !payment) {
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
    await supabase
      .from('payments')
      .update({
        metadata: {
          ...payment.metadata,
          post_payment_processed: true,
          post_payment_at: new Date().toISOString()
        }
      })
      .eq('id', paymentUuid);

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

  // TODO: Implement email/SMS sending
  // Example with SendGrid, Twilio, etc.

  const email = payment.metadata?.email || payment.user_id;
  const serviceName = payment.metadata?.service || 'AUTO-V Service';

  // Simulate sending
  logger.debug('📧 Confirmation details', {
    to: email,
    subject: `Payment Confirmation - ${payment.payment_id}`,
    amount: payment.amount,
    receipt: payment.mpesa_code,
    service: serviceName
  });

  // Return early - implement your actual notification logic
  return;
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
    reference: payment.metadata?.reference,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString()
  };

  const { data, error } = await supabase
    .from('service_requests')
    .insert(serviceData)
    .select()
    .single();

  if (error) {
    logger.error('❌ Failed to create service request', {
      paymentId: payment.payment_id,
      error: error.message
    });
    throw new Error(`Failed to create service request: ${error.message}`);
  }

  logger.info(`✅ Service request created: ${data.id}`);
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
    const { data: payment, error } = await supabase
      .from('payments')
      .select('*')
      .eq('checkout_request_id', checkoutId)
      .single();

    if (error || !payment) {
      return { success: false, error: 'Payment not found' };
    }

    if (payment.status === 'pending') {
      const { error: updateError } = await supabase
        .from('payments')
        .update({
          status: 'timeout',
          mpesa_result_code: '1037',
          mpesa_result_desc: 'Transaction timed out',
          updated_at: new Date().toISOString()
        })
        .eq('id', payment.id);

      if (updateError) {
        return { success: false, error: updateError.message };
      }

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
    const { data: payment, error } = await supabase
      .from('payments')
      .select('*')
      .eq('checkout_request_id', checkoutId)
      .single();

    if (error || !payment) {
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

import { Request, Response } from 'express';

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

// ─── Exports ──────────────────────────────────────────────────

export default {
  handleMpesaCallback,
  handleMpesaTimeout,
  verifyMpesaTransaction,
  mpesaCallbackHandler
};
