CREATE TABLE IF NOT EXISTS vpn_nodes (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    xui_base_url TEXT NOT NULL,
    xui_username TEXT NOT NULL,
    xui_password TEXT NOT NULL,
    xui_inbound_id INTEGER NOT NULL,
    backend_host TEXT NOT NULL,
    backend_port INTEGER NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    lb_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    needs_backfill BOOLEAN NOT NULL DEFAULT FALSE,
    last_health_at TIMESTAMPTZ,
    last_health_ok BOOLEAN,
    last_health_error TEXT,
    last_reality_public_key TEXT,
    last_reality_short_id TEXT,
    last_reality_sni TEXT,
    last_reality_fingerprint TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_vpn_nodes_lb_enabled_is_active
    ON vpn_nodes (lb_enabled, is_active);

CREATE TABLE IF NOT EXISTS vpn_node_clients (
    id BIGSERIAL PRIMARY KEY,
    node_id BIGINT NOT NULL REFERENCES vpn_nodes(id) ON DELETE CASCADE,
    subscription_id BIGINT NOT NULL REFERENCES subscriptions(id) ON DELETE CASCADE,
    client_uuid UUID NOT NULL,
    client_email TEXT NOT NULL,
    xui_sub_id TEXT,
    desired_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    desired_expires_at TIMESTAMPTZ NOT NULL,
    observed_enabled BOOLEAN,
    observed_expires_at TIMESTAMPTZ,
    sync_state TEXT NOT NULL DEFAULT 'pending',
    last_synced_at TIMESTAMPTZ,
    last_error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (node_id, subscription_id)
);

CREATE INDEX IF NOT EXISTS idx_vpn_node_clients_node_id_sync_state
    ON vpn_node_clients (node_id, sync_state);

CREATE INDEX IF NOT EXISTS idx_vpn_node_clients_subscription_id
    ON vpn_node_clients (subscription_id);
