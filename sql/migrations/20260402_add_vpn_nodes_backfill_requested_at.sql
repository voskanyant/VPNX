ALTER TABLE vpn_nodes
ADD COLUMN IF NOT EXISTS backfill_requested_at TIMESTAMPTZ;
