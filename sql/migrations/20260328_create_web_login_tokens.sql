CREATE TABLE IF NOT EXISTS web_login_tokens (
    id BIGSERIAL PRIMARY KEY,
    token TEXT NOT NULL UNIQUE,
    telegram_id BIGINT NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    consumed_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_web_login_tokens_telegram_id
    ON web_login_tokens (telegram_id);

CREATE INDEX IF NOT EXISTS idx_web_login_tokens_expires_at
    ON web_login_tokens (expires_at);

CREATE INDEX IF NOT EXISTS idx_web_login_tokens_consumed_at
    ON web_login_tokens (consumed_at);
