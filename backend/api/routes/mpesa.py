# api/routes/mpesa.py – M-Pesa Routes (PRODUCTION READY)

import os
import logging
import uuid
import json
import hashlib
from functools import wraps
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from flask import Blueprint, request, jsonify, current_app
from services.supabase_client import get_supabase
from services.mpesa import (
    initiate_stk_push,
    query_payment_status,
    is_mpesa_configured,
    get_mpesa_token,
    handle_mpesa_callback,
    sanitize_log_data,
    verify_safaricom_ip
)
from api.auth_middleware import require_auth, require_admin
import redis
import time

logger = logging.getLogger(__name__)
mpesa_bp = Blueprint('mpesa', __name__)

# ─── REDIS CONNECTION (for distributed locks) ──────────────
REDIS_URL = os.getenv('REDIS_URL', None)
redis_client = None
if REDIS_URL:
    try:
        redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        logger.info("✅ Redis connected for distributed locks")
    except Exception as e:
        logger.warning(f"⚠️ Redis connection failed: {e}")


# ─── PAYMENT STATE MACHINE ──────────────────────────────────
class PaymentStatus(Enum):
    """Strict payment state machine."""
    CREATED = "created"
    STK_SENT = "stk_sent"
    AWAITING_CALLBACK = "awaiting_callback"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"
    REFUNDED = "refunded"

    @classmethod
    def transitions(cls):
        """Define allowed state transitions."""
        return {
            cls.CREATED: [cls.STK_SENT, cls.FAILED],
            cls.STK_SENT: [cls.AWAITING_CALLBACK, cls.FAILED],
            cls.AWAITING_CALLBACK: [cls.COMPLETED, cls.FAILED, cls.EXPIRED],
            cls.COMPLETED: [cls.REFUNDED],
            cls.FAILED: [],
            cls.EXPIRED: [],
            cls.REFUNDED: []
        }

    def can_transition_to(self, new_state):
        """Check if transition is allowed."""
        return new_state in self.transitions().get(self, [])


# ─── Helper: Distributed Lock ──────────────────────────────
def acquire_lock(lock_key: str, timeout: int = 30) -> bool:
    """Acquire a distributed lock using Redis."""
    if not redis_client:
        return True  # Fallback: no lock
    try:
        return redis_client.set(lock_key, "locked", nx=True, ex=timeout)
    except Exception as e:
        logger.warning(f"Lock acquire failed: {e}")
        return True


def release_lock(lock_key: str) -> bool:
    """Release a distributed lock."""
    if not redis_client:
        return True
    try:
        return bool(redis_client.delete(lock_key))
    except Exception as e:
        logger.warning(f"Lock release failed: {e}")
        return True


# ─── Helper: Generate True Idempotency Key ─────────────────
def generate_idempotency_key(user_id: str, amount: int, service: str, phone: str, purpose: str) -> str:
    """
    Generate a TRUE idempotency key - stable and deterministic.
    Same inputs = same key forever.
    """
    raw = f"{user_id}:{amount}:{service}:{phone}:{purpose}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


# ─── Helper: Safe Payment Creation (DB-Level Idempotency) ──
def create_payment_record(user_id: str, data: dict) -> tuple:
    """
    Create a payment record with database-level idempotency.
    Uses UNIQUE constraint on idempotency_key for race condition safety.
    Returns (payment, error_response, status_code)
    """
    try:
        supabase = get_supabase()
        amount_int = int(data['amount'])
        idempotency_key = generate_idempotency_key(
            user_id,
            amount_int,
            data['service'],
            data['phone'],
            data['purpose']
        )

        # ─── TRY INSERT WITH UNIQUE CONSTRAINT ──────────────────
        payment_data = {
            'user_id': user_id,
            'service_type': data['service'],
            'purpose': data['purpose'],
            'amount': amount_int,
            'phone': data['phone'],
            'client_type': data.get('client_type', 'individual'),
            'status': PaymentStatus.CREATED.value,
            'reference': f'AUTO-{uuid.uuid4().hex[:8].upper()}',
            'idempotency_key': idempotency_key,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }

        response = supabase.table('payments').insert(payment_data).execute()

        # ─── CHECK FOR DUPLICATE ──────────────────────────────────
        if hasattr(response, 'error') and response.error:
            if 'duplicate key' in str(response.error).lower():
                logger.info(f"ℹ️ Duplicate detected via DB constraint")
                # Retrieve existing payment
                retry = supabase.table('payments')\
                    .select('*')\
                    .eq('idempotency_key', idempotency_key)\
                    .execute()
                if retry.data:
                    logger.info(f"✅ Retrieved existing payment: {retry.data[0]['id'][:8]}")
                    return retry.data[0], None, 200
            logger.error(f"❌ Supabase insert error: {response.error}")
            return None, {'error': 'Database error', 'details': str(response.error)}, 500

        if not response.data:
            logger.error("❌ No data returned from insert")
            return None, {'error': 'Failed to create payment record'}, 500

        payment = response.data[0]
        log_payment_event(payment['id'], 'created', {'idempotency_key': idempotency_key})
        logger.info(f"✅ Created payment: {payment['id'][:8]}")
        return payment, None, 200

    except Exception as e:
        logger.error(f"❌ Payment creation error: {e}", exc_info=True)
        return None, {'error': 'Failed to create payment'}, 500


# ─── Helper: Transition Payment State ──────────────────────
def transition_payment_state(payment_id: str, new_status: PaymentStatus, details: dict = None) -> bool:
    """
    Transition payment to a new state with validation.
    """
    try:
        supabase = get_supabase()

        # ─── Get current status ──────────────────────────────────
        current = supabase.table('payments')\
            .select('status')\
            .eq('id', payment_id)\
            .execute()

        if not current.data:
            logger.error(f"❌ Payment {payment_id[:8]} not found for state transition")
            return False

        current_status = current.data[0].get('status')
        current_enum = PaymentStatus(current_status) if current_status in [s.value for s in PaymentStatus] else None

        if not current_enum:
            logger.error(f"❌ Invalid current status: {current_status}")
            return False

        # ─── Validate transition ──────────────────────────────────
        if not current_enum.can_transition_to(new_status):
            logger.warning(f"⚠️ Invalid state transition: {current_status} → {new_status.value}")
            return False

        # ─── Execute transition ──────────────────────────────────
        update_data = {
            'status': new_status.value,
            'updated_at': datetime.now().isoformat()
        }

        if new_status == PaymentStatus.COMPLETED:
            update_data['completed_at'] = datetime.now().isoformat()

        result = supabase.table('payments')\
            .update(update_data)\
            .eq('id', payment_id)\
            .execute()

        if hasattr(result, 'error') and result.error:
            logger.error(f"❌ State transition error: {result.error}")
            return False

        log_payment_event(payment_id, f'status_{new_status.value}', details or {})
        logger.info(f"✅ Payment {payment_id[:8]} transitioned: {current_status} → {new_status.value}")
        return True

    except Exception as e:
        logger.error(f"❌ State transition error: {e}", exc_info=True)
        return False


# ─── Helper: Log Payment Event ─────────────────────────────
def log_payment_event(payment_id: str, event: str, details: dict = None):
    """Log payment events to dedicated table."""
    try:
        supabase = get_supabase()
        supabase.table('payment_events').insert({
            'payment_id': payment_id,
            'event': event,
            'details': details or {},
            'created_at': datetime.now().isoformat()
        }).execute()
    except Exception as e:
        logger.warning(f"Failed to log payment event: {e}")


# ─── Helper: Retry with Exponential Backoff ────────────────
def retry_mpesa_query(checkout_id: str, max_retries: int = 3) -> dict:
    """Query M-Pesa with retry and exponential backoff."""
    delays = [1, 2, 4]  # seconds

    for attempt in range(max_retries):
        try:
            result = query_payment_status(checkout_id)
            # Check if we got a valid response
            if result.get('ResultCode') is not None:
                return result
            if attempt < max_retries - 1:
                time.sleep(delays[attempt])
        except Exception as e:
            logger.warning(f"Query attempt {attempt+1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(delays[attempt])

    raise Exception(f"Failed to query M-Pesa after {max_retries} attempts")


# ─── =========================================================───
# ─── ROUTES ──────────────────────────────────────────────────────
# ─── =========================================================───

@mpesa_bp.route('/config-status', methods=['GET'])
def config_status():
    """Check M-Pesa configuration status."""
    try:
        result = {
            'is_configured': is_mpesa_configured(),
            'environment': os.getenv('MPESA_ENV', 'not_set'),
            'shortcode': os.getenv('MPESA_SHORTCODE', 'not_set'),
            'callback_url': os.getenv('MPESA_CALLBACK_URL', 'not_set'),
            'redis_connected': bool(redis_client),
            'variables': {
                'MPESA_CONSUMER_KEY': '✅' if os.getenv('MPESA_CONSUMER_KEY') else '❌',
                'MPESA_CONSUMER_SECRET': '✅' if os.getenv('MPESA_CONSUMER_SECRET') else '❌',
                'MPESA_PASSKEY': '✅' if os.getenv('MPESA_PASSKEY') else '❌',
                'MPESA_SHORTCODE': '✅' if os.getenv('MPESA_SHORTCODE') else '❌',
                'MPESA_CALLBACK_URL': '✅' if os.getenv('MPESA_CALLBACK_URL') else '❌',
            }
        }

        if result['is_configured']:
            try:
                token = get_mpesa_token()
                result['token_test'] = '✅ Success'
                result['token_preview'] = token[:20] + '...' if token else None
            except Exception as e:
                result['token_test'] = f'❌ Failed: {str(e)}'

        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Config status error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


# ─── Initiate Payment ────────────────────────────────────────
@mpesa_bp.route('/initiate', methods=['POST', 'OPTIONS'])
@require_auth
def initiate_payment(user):
    """
    Initiate M-Pesa STK Push payment.
    """
    # ─── Handle OPTIONS preflight ───────────────────────────────
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"}), 200

    try:
        data = request.get_json()
        logger.info(f"📥 Payment initiation request from user {user['id'][:8]}")

        # ─── Validate required fields ──────────────────────────
        required = ['phone', 'amount', 'service', 'purpose']
        for field in required:
            if not data.get(field):
                return jsonify({'error': f'Missing required field: {field}'}), 400

        phone = data.get('phone')
        amount = float(data.get('amount'))
        service = data.get('service')
        purpose = data.get('purpose')
        client_type = data.get('client_type', 'individual')

        # ─── Validate amount ────────────────────────────────────
        if amount <= 0:
            return jsonify({'error': 'Amount must be greater than 0'}), 400

        amount_int = int(round(amount))
        if amount_int < 1:
            return jsonify({'error': 'Amount must be at least 1 KES'}), 400

        # ─── Check M-Pesa configuration ──────────────────────────
        if not is_mpesa_configured():
            logger.error("❌ M-Pesa not configured")
            return jsonify({
                'error': 'M-Pesa is not configured. Please contact support.',
                'code': 'MPESA_NOT_CONFIGURED'
            }), 503

        # ─── Acquire distributed lock ────────────────────────────
        lock_key = f"payment:{user['id']}:{service}"
        if not acquire_lock(lock_key, timeout=30):
            return jsonify({'error': 'Another payment is in progress. Please wait.'}), 429

        try:
            # ─── Create payment record (with idempotency) ────────────
            payment, error_response, status_code = create_payment_record(
                user['id'],
                {
                    'phone': phone,
                    'amount': amount_int,
                    'service': service,
                    'purpose': purpose,
                    'client_type': client_type
                }
            )

            if error_response:
                return jsonify(error_response), status_code

            payment_id = payment['id']

            # ─── Check if payment already has checkout_id ──────────
            if payment.get('checkout_request_id'):
                logger.info(f"ℹ️ Payment {payment_id[:8]} already has CheckoutID")
                return jsonify({
                    'payment_id': payment_id,
                    'checkout_id': payment['checkout_request_id'],
                    'merchant_request_id': payment.get('merchant_request_id'),
                    'status': payment.get('status', 'pending'),
                    'message': 'Payment already initiated. Check your phone for the STK Push.'
                }), 200

            # ─── Transition to STK_SENT state ──────────────────────
            if not transition_payment_state(payment_id, PaymentStatus.STK_SENT):
                return jsonify({'error': 'Payment state transition failed'}), 500

            # ─── Initiate STK Push ──────────────────────────────────
            try:
                mpesa_response = initiate_stk_push(
                    phone=phone,
                    amount=float(amount_int),
                    payment_id=payment_id,
                    service=service
                )

                checkout_id = mpesa_response.get('CheckoutRequestID')
                merchant_request_id = mpesa_response.get('MerchantRequestID')

                if not checkout_id:
                    logger.error(f"❌ No CheckoutRequestID for payment {payment_id[:8]}")
                    transition_payment_state(payment_id, PaymentStatus.FAILED, {'error': 'No CheckoutRequestID'})
                    return jsonify({
                        'error': 'Failed to initiate STK Push. Please try again.',
                        'payment_id': payment_id
                    }), 400

                # ─── Update payment with checkout ID ──────────────────
                supabase = get_supabase()
                update_result = supabase.table('payments').update({
                    'checkout_request_id': checkout_id,
                    'merchant_request_id': merchant_request_id,
                    'updated_at': datetime.now().isoformat()
                }).eq('id', payment_id).execute()

                if hasattr(update_result, 'error') and update_result.error:
                    logger.error(f"❌ Update error: {update_result.error}")

                # ─── Transition to AWAITING_CALLBACK ──────────────────
                transition_payment_state(payment_id, PaymentStatus.AWAITING_CALLBACK, {
                    'checkout_id': checkout_id,
                    'merchant_request_id': merchant_request_id
                })

                logger.info(f"✅ STK Push sent for payment {payment_id[:8]}, CheckoutID: {checkout_id[:8]}")

                return jsonify({
                    'payment_id': payment_id,
                    'checkout_id': checkout_id,
                    'merchant_request_id': merchant_request_id,
                    'status': 'pending',
                    'message': 'STK Push sent to your phone. Please confirm the transaction.'
                }), 200

            except Exception as e:
                transition_payment_state(payment_id, PaymentStatus.FAILED, {'error': str(e)})
                logger.error(f"❌ STK Push failed for payment {payment_id[:8]}: {e}")
                return jsonify({
                    'error': str(e),
                    'payment_id': payment_id
                }), 400

        finally:
            release_lock(lock_key)

    except ValueError as e:
        return jsonify({'error': f'Invalid amount: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"❌ Payment initiation error: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


# ─── Get Payment Status ──────────────────────────────────────
@mpesa_bp.route('/status/<payment_id>', methods=['GET', 'OPTIONS'])
@require_auth
def get_payment_status(user, payment_id):
    """
    Get the current status of a payment from Supabase and query M-Pesa if pending.
    """
    # ─── Handle OPTIONS preflight ───────────────────────────────
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"}), 200

    try:
        supabase = get_supabase()

        response = supabase.table('payments')\
            .select('*')\
            .eq('id', payment_id)\
            .eq('user_id', user['id'])\
            .execute()

        if hasattr(response, 'error') and response.error:
            logger.error(f"❌ DB error: {response.error}")
            return jsonify({'error': 'Database error'}), 500

        if not response.data:
            return jsonify({'error': 'Payment not found'}), 404

        payment = response.data[0]
        status = payment.get('status')
        logger.info(f"📊 Payment {payment_id[:8]} status: {status}")

        # ─── Query M-Pesa if awaiting callback ──────────────────
        if status in [PaymentStatus.AWAITING_CALLBACK.value, PaymentStatus.STK_SENT.value]:
            try:
                checkout_id = payment.get('checkout_request_id')
                if not checkout_id:
                    return jsonify({
                        'payment_id': payment_id,
                        'status': status,
                        'amount': payment.get('amount'),
                        'service_type': payment.get('service_type'),
                        'phone': payment.get('phone'),
                        'message': 'No checkout ID available'
                    }), 200

                logger.info(f"🔍 Querying M-Pesa for: {checkout_id[:8]}")

                # ─── Retry with exponential backoff ──────────────────
                mpesa_status = retry_mpesa_query(checkout_id)
                result_code = mpesa_status.get('ResultCode')
                result_desc = mpesa_status.get('ResultDesc')
                transaction_id = mpesa_status.get('TransactionID')

                logger.info(f"📥 M-Pesa query result: {result_code}")

                if str(result_code) == '0':
                    # ✅ Payment completed
                    transition_payment_state(payment_id, PaymentStatus.COMPLETED, {
                        'transaction_id': transaction_id,
                        'result_desc': result_desc
                    })

                    # Update additional fields
                    supabase.table('payments').update({
                        'transaction_id': transaction_id,
                        'mpesa_result_code': str(result_code),
                        'mpesa_result_desc': result_desc,
                        'completed_at': datetime.now().isoformat()
                    }).eq('id', payment_id).execute()

                    logger.info(f"✅ Payment {payment_id[:8]} completed! TXN: {transaction_id[:8] if transaction_id else 'N/A'}")

                    return jsonify({
                        'payment_id': payment_id,
                        'status': 'completed',
                        'amount': payment.get('amount'),
                        'service_type': payment.get('service_type'),
                        'phone': payment.get('phone'),
                        'transaction_id': transaction_id,
                        'message': 'Payment completed'
                    }), 200

                elif str(result_code) in ['1037', '1032']:
                    # ❌ User cancelled
                    transition_payment_state(payment_id, PaymentStatus.FAILED, {'result_code': result_code})
                    logger.warning(f"⚠️ Payment {payment_id[:8]} cancelled: {result_desc}")

                    return jsonify({
                        'payment_id': payment_id,
                        'status': 'failed',
                        'amount': payment.get('amount'),
                        'service_type': payment.get('service_type'),
                        'phone': payment.get('phone'),
                        'message': result_desc or 'Transaction cancelled'
                    }), 200

                elif str(result_code) == '2001':
                    # ⏳ Still pending
                    logger.info(f"⏳ Payment {payment_id[:8]} still pending at M-Pesa")
                    return jsonify({
                        'payment_id': payment_id,
                        'status': 'pending',
                        'amount': payment.get('amount'),
                        'service_type': payment.get('service_type'),
                        'phone': payment.get('phone'),
                        'checkout_request_id': checkout_id,
                        'message': 'Transaction still processing at M-Pesa'
                    }), 200

                else:
                    # ❌ Failed
                    transition_payment_state(payment_id, PaymentStatus.FAILED, {'result_code': result_code})
                    logger.warning(f"❌ Payment {payment_id[:8]} failed: {result_desc}")

                    return jsonify({
                        'payment_id': payment_id,
                        'status': 'failed',
                        'amount': payment.get('amount'),
                        'service_type': payment.get('service_type'),
                        'phone': payment.get('phone'),
                        'message': result_desc or 'Transaction failed'
                    }), 200

            except Exception as e:
                logger.warning(f"⚠️ Failed to query M-Pesa status: {e}")
                return jsonify({
                    'payment_id': payment_id,
                    'status': 'pending',
                    'amount': payment.get('amount'),
                    'service_type': payment.get('service_type'),
                    'phone': payment.get('phone'),
                    'checkout_request_id': payment.get('checkout_request_id'),
                    'message': 'Unable to verify status with M-Pesa'
                }), 200

        # ─── Return current status ──────────────────────────────
        return jsonify({
            'payment_id': payment_id,
            'status': status,
            'amount': payment.get('amount'),
            'service_type': payment.get('service_type'),
            'phone': payment.get('phone'),
            'transaction_id': payment.get('transaction_id'),
            'mpesa_receipt': payment.get('mpesa_receipt_number'),
            'result_code': payment.get('mpesa_result_code'),
            'result_desc': payment.get('mpesa_result_desc'),
            'checkout_request_id': payment.get('checkout_request_id'),
            'completed_at': payment.get('completed_at')
        }), 200

    except Exception as e:
        logger.error(f"❌ Error getting payment status: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


# ─── M-Pesa Callback ─────────────────────────────────────────
@mpesa_bp.route('/callback', methods=['POST'])
def mpesa_callback():
    """
    Handle M-Pesa callback from Safaricom.
    Uses the hardened callback handler from services.mpesa.
    """
    try:
        # ─── Log raw request (sanitized) ────────────────────────
        raw_data = request.get_data(as_text=True)
        logger.info("=" * 60)
        logger.info("📥 M-PESA CALLBACK RECEIVED")
        logger.info(f"Raw data length: {len(raw_data)}")
        logger.info(f"Client IP: {request.remote_addr}")

        # ─── Parse JSON ────────────────────────────────────────────
        data = request.get_json()
        if not data:
            logger.error("❌ No JSON data in callback")
            return jsonify({'ResultCode': 1, 'ResultDesc': 'No data'}), 400

        # ─── Sanitize before logging ──────────────────────────────
        try:
            sanitized = sanitize_log_data(data)
            logger.info(f"Callback data (sanitized): {json.dumps(sanitized, indent=2)[:500]}")
        except Exception as e:
            logger.warning(f"Could not sanitize callback data: {e}")

        # ─── Extract checkout_id early ──────────────────────────
        checkout_id = None
        try:
            stk = data.get('Body', {}).get('stkCallback', {})
            checkout_id = stk.get('CheckoutRequestID')
        except:
            pass

        # ─── Call the hardened callback handler with IP ──────────
        result = handle_mpesa_callback(
            callback_data=data,
            client_ip=request.remote_addr
        )

        # ─── Log result ────────────────────────────────────────────
        if result.get('ResultCode') == 0:
            logger.info(f"✅ Callback processed successfully for {checkout_id[:8] if checkout_id else 'unknown'}")
        else:
            logger.warning(f"⚠️ Callback processing failed: {result.get('ResultDesc')}")

        return jsonify({
            'ResultCode': result.get('ResultCode', 0),
            'ResultDesc': result.get('ResultDesc', 'Success')
        }), 200

    except Exception as e:
        logger.error(f"❌ Callback error: {e}", exc_info=True)
        return jsonify({'ResultCode': 1, 'ResultDesc': str(e)}), 200


# ─── Admin: Force Complete Payment ──────────────────────────
@mpesa_bp.route('/force-complete/<payment_id>', methods=['POST'])
@require_admin
def force_complete_payment(user, payment_id):
    """
    Force complete a payment (admin only).
    """
    try:
        supabase = get_supabase()

        # ─── Check if payment exists ──────────────────────────────
        check = supabase.table('payments')\
            .select('status')\
            .eq('id', payment_id)\
            .execute()

        if hasattr(check, 'error') and check.error:
            return jsonify({'error': 'Database error'}), 500

        if not check.data:
            return jsonify({'error': 'Payment not found'}), 404

        current_status = check.data[0].get('status')

        # ─── Transition to COMPLETED ──────────────────────────────
        if transition_payment_state(payment_id, PaymentStatus.COMPLETED, {'admin_id': user['id']}):
            # Update additional fields
            supabase.table('payments').update({
                'mpesa_result_desc': f'Force completed by admin {user["id"][:8]}',
                'completed_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }).eq('id', payment_id).execute()

            logger.info(f"✅ Force completed payment {payment_id[:8]} by admin {user['id'][:8]}")
            return jsonify({'success': True, 'message': 'Payment force completed'}), 200

        if current_status == PaymentStatus.COMPLETED.value:
            return jsonify({'success': True, 'message': 'Payment was already completed'}), 200

        return jsonify({'error': 'Failed to transition payment state'}), 500

    except Exception as e:
        logger.error(f"❌ Force complete error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


# ─── Admin: Payment Events Log ──────────────────────────────
@mpesa_bp.route('/events/<payment_id>', methods=['GET'])
@require_admin
def get_payment_events(user, payment_id):
    """
    Get payment event history (admin only).
    """
    try:
        supabase = get_supabase()

        response = supabase.table('payment_events')\
            .select('*')\
            .eq('payment_id', payment_id)\
            .order('created_at', desc=True)\
            .execute()

        if hasattr(response, 'error') and response.error:
            return jsonify({'error': 'Database error'}), 500

        return jsonify({
            'payment_id': payment_id,
            'events': response.data or []
        }), 200

    except Exception as e:
        logger.error(f"❌ Events error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


# ─── Admin: Reconciliation Job ──────────────────────────────
@mpesa_bp.route('/reconcile', methods=['POST'])
@require_admin
def reconcile_payments(user):
    """
    Reconcile pending payments (admin only).
    Scans payments in AWAITING_CALLBACK state and queries M-Pesa.
    """
    try:
        supabase = get_supabase()

        # ─── Find pending payments ──────────────────────────────
        response = supabase.table('payments')\
            .select('*')\
            .eq('status', PaymentStatus.AWAITING_CALLBACK.value)\
            .gte('created_at', (datetime.now() - timedelta(days=7)).isoformat())\
            .execute()

        if hasattr(response, 'error') and response.error:
            return jsonify({'error': 'Database error'}), 500

        pending = response.data or []
        results = []

        for payment in pending:
            payment_id = payment['id']
            checkout_id = payment.get('checkout_request_id')

            if not checkout_id:
                continue

            try:
                # ─── Query M-Pesa ──────────────────────────────────
                mpesa_status = retry_mpesa_query(checkout_id, max_retries=2)
                result_code = mpesa_status.get('ResultCode')
                transaction_id = mpesa_status.get('TransactionID')

                if str(result_code) == '0':
                    transition_payment_state(payment_id, PaymentStatus.COMPLETED, {
                        'reconciled': True,
                        'transaction_id': transaction_id
                    })
                    supabase.table('payments').update({
                        'transaction_id': transaction_id,
                        'mpesa_result_code': str(result_code),
                        'completed_at': datetime.now().isoformat()
                    }).eq('id', payment_id).execute()
                    results.append({'payment_id': payment_id, 'status': 'completed', 'transaction_id': transaction_id})

                elif str(result_code) in ['1037', '1032', '2001']:
                    # Still pending or cancelled
                    results.append({'payment_id': payment_id, 'status': 'pending', 'result_code': result_code})

                else:
                    transition_payment_state(payment_id, PaymentStatus.FAILED, {'reconciled': True})
                    results.append({'payment_id': payment_id, 'status': 'failed', 'result_code': result_code})

            except Exception as e:
                logger.error(f"❌ Reconcile error for {payment_id[:8]}: {e}")
                results.append({'payment_id': payment_id, 'status': 'error', 'error': str(e)})

        return jsonify({
            'total_checked': len(pending),
            'results': results
        }), 200

    except Exception as e:
        logger.error(f"❌ Reconciliation error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


# ─── Debug: Callback Tester ─────────────────────────────────
@mpesa_bp.route('/callback-debug', methods=['GET', 'POST'])
def mpesa_callback_debug():
    """
    Debug endpoint to see what M-Pesa is sending.
    """
    if request.method == 'POST':
        try:
            data = request.get_json()
            logger.info("=" * 60)
            logger.info("🔍 CALLBACK DEBUG - FULL PAYLOAD:")

            if data:
                try:
                    sanitized = sanitize_log_data(data)
                    logger.info(json.dumps(sanitized, indent=2))
                except:
                    logger.info(str(data)[:1000])
            else:
                logger.info("No data")

            logger.info("=" * 60)

            checkout_id = None
            result_code = None
            if data and 'Body' in data:
                stk = data.get('Body', {}).get('stkCallback', {})
                checkout_id = stk.get('CheckoutRequestID')
                result_code = stk.get('ResultCode')
                logger.info(f"📊 Extracted: CheckoutID={checkout_id}, ResultCode={result_code}")

            return jsonify({
                'status': 'received',
                'checkout_id': checkout_id,
                'result_code': result_code,
                'message': 'Debug callback received'
            }), 200

        except Exception as e:
            logger.error(f"Debug callback error: {e}", exc_info=True)
            return jsonify({'error': str(e)}), 500

    return jsonify({
        'message': 'Send POST to this endpoint for debugging',
        'usage': 'curl -X POST https://auto-v.onrender.com/api/mpesa/callback-debug -H "Content-Type: application/json" -d \'{"test":"data"}\''
    }), 200
