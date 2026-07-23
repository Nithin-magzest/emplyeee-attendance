-- Optional hardening: run the app as a scoped Postgres role instead of the
-- RDS master user (var.db_username in terraform/main.tf). The master user
-- has broad privileges (create/drop any database object, alter other
-- roles); a compromised app connection (e.g. via a future SQL-injection bug
-- that DOES slip through) is limited to what this role can do instead.
--
-- The app's schema-per-tenant self-signup flow (create_tenant_schema() in
-- database.py, used by /create_org) needs CREATE on the database — so this
-- role can't be locked down to a single schema the way a typical
-- least-privilege app role would be. It still meaningfully reduces blast
-- radius: no CREATEDB, no CREATEROLE, no superuser, and it can't touch
-- other databases on the same RDS instance.
--
-- How to apply:
--   1. Connect as the RDS master user:
--        psql "host=<rds_endpoint> port=5432 dbname=<db_name> user=<master_user> sslmode=require"
--   2. Replace the password below, then run this whole file:
--        \i least_privilege_role.sql
--   3. Update DB_USER/DB_PASS in your deployed .env (or the db_password
--      secret used by deploy.sh) to the new role's credentials, then
--      restart the app.
--   4. Verify the app still works end-to-end (login, check-in, /create_org)
--      before removing the master user's own credentials from anywhere
--      they might be cached.

CREATE ROLE attendance_app WITH LOGIN PASSWORD 'CHANGE_ME_BEFORE_RUNNING';

-- Needed for create_tenant_schema()/CREATE SCHEMA IF NOT EXISTS att_master
-- at startup and on every /create_org signup.
GRANT CREATE, CONNECT ON DATABASE current_database() TO attendance_app;

-- Grant full DML/DDL within schemas that already exist (public + any
-- already-provisioned tenant schemas), and set defaults so newly-created
-- tenant schemas automatically grant the same to this role going forward
-- (a schema this role itself creates already owns it, so this mainly
-- matters for schemas pre-existing before this role was introduced).
DO $$
DECLARE
    schema_name text;
BEGIN
    FOR schema_name IN
        SELECT nspname FROM pg_namespace
        WHERE nspname NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
          AND nspname NOT LIKE 'pg_temp_%'
          AND nspname NOT LIKE 'pg_toast_temp_%'
    LOOP
        EXECUTE format('GRANT USAGE, CREATE ON SCHEMA %I TO attendance_app', schema_name);
        EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA %I TO attendance_app', schema_name);
        EXECUTE format('GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA %I TO attendance_app', schema_name);
        EXECUTE format('ALTER DEFAULT PRIVILEGES IN SCHEMA %I GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO attendance_app', schema_name);
        EXECUTE format('ALTER DEFAULT PRIVILEGES IN SCHEMA %I GRANT USAGE, SELECT ON SEQUENCES TO attendance_app', schema_name);
    END LOOP;
END $$;

-- Explicitly confirm what this role can NOT do (documentation, not SQL —
-- these are simply never granted above): CREATEDB, CREATEROLE, SUPERUSER,
-- access to any other database on the instance, DROP DATABASE/DROP ROLE.
