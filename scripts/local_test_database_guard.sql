-- Run only in the isolated migratelens_test database as its administrator.
-- This creates a NOLOGIN privilege group, never a login or password.
DO $$
BEGIN
  IF current_database() <> 'migratelens_test' THEN
    RAISE EXCEPTION 'Refusing setup outside migratelens_test';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = 'ml') THEN
    RAISE EXCEPTION 'MigrateLens schema already exists; inspect migration state';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'ml_runtime') THEN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'ml_runtime'
               AND (rolsuper OR rolbypassrls OR rolcreaterole OR rolcreatedb OR rolcanlogin)) THEN
      RAISE EXCEPTION 'Existing ml_runtime role exceeds test privilege-group policy';
    END IF;
  ELSE
    CREATE ROLE ml_runtime NOLOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE;
  END IF;
END $$;
