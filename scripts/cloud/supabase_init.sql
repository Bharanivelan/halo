-- One-time setup of a Supabase project for Halo (D-50). Run as the `postgres` user BEFORE the migrations:
--   psql "<session pooler URL as postgres>" -v app_password='<new strong password>' -f scripts/cloud/supabase_init.sql
-- Safe to run again.
\set ON_ERROR_STOP on

-- Extensions Halo needs. Supabase keeps extensions in the `extensions` schema (on the default search_path).
CREATE EXTENSION IF NOT EXISTS postgis WITH SCHEMA extensions;
CREATE EXTENSION IF NOT EXISTS citext WITH SCHEMA extensions;
CREATE EXTENSION IF NOT EXISTS pg_trgm WITH SCHEMA extensions;

-- The application connects as a NON-owner role so Postgres row-level security applies to it
-- (same as infra/db-init/01-roles.sh locally). `postgres` owns the tables and runs migrations.
SELECT format('CREATE ROLE inhabitr_app LOGIN PASSWORD %L NOSUPERUSER NOBYPASSRLS', :'app_password')
WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'inhabitr_app') \gexec
SELECT format('ALTER ROLE inhabitr_app WITH LOGIN PASSWORD %L', :'app_password') \gexec
ALTER ROLE inhabitr_app SET search_path = public, extensions;
GRANT CONNECT ON DATABASE postgres TO inhabitr_app;
GRANT USAGE ON SCHEMA public TO inhabitr_app;
GRANT USAGE ON SCHEMA extensions TO inhabitr_app;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO inhabitr_app;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO inhabitr_app;

-- Halo has its own API and logins. Supabase's automatic Data API (PostgREST) must not expose Halo's tables
-- (e.g. users with password hashes) to the project's public anon key. Also switch the Data API off in the dashboard.
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon, authenticated;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM anon, authenticated;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA public FROM anon, authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public REVOKE ALL ON TABLES FROM anon, authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public REVOKE ALL ON SEQUENCES FROM anon, authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public REVOKE ALL ON FUNCTIONS FROM anon, authenticated;
