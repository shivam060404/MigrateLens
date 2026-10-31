-- Local development only. Run inside the manually created "MigrateLens" database.
DO $$
BEGIN
  IF current_database() <> 'MigrateLens' THEN
    RAISE EXCEPTION 'Refusing setup outside MigrateLens';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = 'ml') THEN
    RAISE EXCEPTION 'MigrateLens schema already exists; inspect migration state';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'ml_runtime') THEN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'ml_runtime'
               AND (rolsuper OR rolbypassrls OR rolcreaterole OR rolcreatedb OR rolcanlogin)) THEN
      RAISE EXCEPTION 'Existing ml_runtime role exceeds privilege-group policy';
    END IF;
  ELSE
    CREATE ROLE ml_runtime NOLOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE;
  END IF;
END $$;
