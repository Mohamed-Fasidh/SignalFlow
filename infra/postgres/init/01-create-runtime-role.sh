#!/bin/sh
set -eu
: "${APP_DB_PASSWORD:?APP_DB_PASSWORD must be supplied}"
: "${MIGRATOR_DB_PASSWORD:?MIGRATOR_DB_PASSWORD must be supplied}"
psql --set=ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  --set=app_db_password="$APP_DB_PASSWORD" --set=migrator_db_password="$MIGRATOR_DB_PASSWORD" <<'SQL'
CREATE ROLE signalflow_migrator LOGIN PASSWORD :'migrator_db_password' NOSUPERUSER NOBYPASSRLS;
GRANT CONNECT, CREATE ON DATABASE signalflow TO signalflow_migrator;
GRANT USAGE, CREATE ON SCHEMA public TO signalflow_migrator;

CREATE ROLE signalflow_runtime LOGIN PASSWORD :'app_db_password' NOSUPERUSER NOBYPASSRLS;
GRANT CONNECT ON DATABASE signalflow TO signalflow_runtime;
GRANT USAGE ON SCHEMA public TO signalflow_runtime;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO signalflow_runtime;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO signalflow_runtime;
ALTER DEFAULT PRIVILEGES FOR ROLE signalflow_migrator IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO signalflow_runtime;
ALTER DEFAULT PRIVILEGES FOR ROLE signalflow_migrator IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO signalflow_runtime;
SQL
