ALTER TABLE orders
ADD COLUMN IF NOT EXISTS channel TEXT,
ADD COLUMN IF NOT EXISTS payment_method TEXT,
ADD COLUMN IF NOT EXISTS amount_minor BIGINT,
ADD COLUMN IF NOT EXISTS currency_iso TEXT,
ADD COLUMN IF NOT EXISTS card_provider TEXT,
ADD COLUMN IF NOT EXISTS card_payment_id TEXT,
ADD COLUMN IF NOT EXISTS idempotency_key TEXT;

CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_card_payment_id ON orders(card_payment_id);
CREATE INDEX IF NOT EXISTS idx_orders_idempotency_key ON orders(idempotency_key);
