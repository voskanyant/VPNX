-- Prevent duplicate web checkouts with the same idempotency key.
CREATE UNIQUE INDEX IF NOT EXISTS uq_orders_idempotency_key
ON orders(idempotency_key)
WHERE idempotency_key IS NOT NULL;

-- Ensure one pending web order per user/payment method at a time.
CREATE UNIQUE INDEX IF NOT EXISTS uq_orders_pending_web_user_method
ON orders(user_id, channel, payment_method)
WHERE status = 'pending'
  AND channel = 'web'
  AND payment_method IS NOT NULL;

