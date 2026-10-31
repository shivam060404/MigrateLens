-- Owner-reviewed local provisioning only; password is entered separately in pgAdmin.
-- This does not restrict PUBLIC privileges on unrelated databases in the cluster.
BEGIN;
SET LOCAL statement_timeout = '5s';
DO $$
BEGIN
  IF current_database() <> 'MigrateLens' THEN
    RAISE EXCEPTION 'Refusing login setup outside MigrateLens';
  END IF;
  IF (SELECT version_num FROM public.alembic_version) IS DISTINCT FROM '0001_tenant_control' THEN
    RAISE EXCEPTION 'Expected migrated development schema';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'ml_runtime' AND NOT rolcanlogin) THEN
    RAISE EXCEPTION 'Expected NOLOGIN ml_runtime privilege group';
  END IF;
  IF EXISTS (
    SELECT 1 FROM pg_roles
    WHERE pg_has_role('ml_runtime', oid, 'MEMBER')
      AND (rolsuper OR rolbypassrls OR rolcreaterole OR rolcreatedb OR rolreplication)
  ) THEN
    RAISE EXCEPTION 'Runtime privilege group has elevated membership';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'ml_development') THEN
    RAISE EXCEPTION 'Existing ml_development role requires owner inspection';
  END IF;
END $$;
CREATE ROLE ml_development LOGIN INHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE
  NOREPLICATION NOBYPASSRLS CONNECTION LIMIT 15 PASSWORD NULL;
GRANT ml_runtime TO ml_development WITH ADMIN FALSE;
GRANT CONNECT ON DATABASE "MigrateLens" TO ml_development;
ALTER ROLE ml_development IN DATABASE "MigrateLens" SET statement_timeout = '15s';
ALTER ROLE ml_development IN DATABASE "MigrateLens" SET idle_in_transaction_session_timeout = '30s';
COMMIT;
