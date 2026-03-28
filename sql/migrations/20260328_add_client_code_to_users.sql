ALTER TABLE users
ADD COLUMN IF NOT EXISTS client_code TEXT;

CREATE OR REPLACE FUNCTION set_users_client_code()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.client_code IS NULL OR NEW.client_code = '' THEN
        NEW.client_code := 'VX-' || LPAD(NEW.id::text, 6, '0');
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_set_users_client_code ON users;
CREATE TRIGGER trg_set_users_client_code
BEFORE INSERT ON users
FOR EACH ROW
EXECUTE FUNCTION set_users_client_code();

UPDATE users
SET client_code = 'VX-' || LPAD(id::text, 6, '0')
WHERE client_code IS NULL;

ALTER TABLE users
ALTER COLUMN client_code SET NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'users_client_code_key'
    ) THEN
        ALTER TABLE users
        ADD CONSTRAINT users_client_code_key UNIQUE (client_code);
    END IF;
END $$;
