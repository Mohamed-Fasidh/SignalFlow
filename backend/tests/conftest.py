import os

# Unit tests use SQLite so test collection does not require a local PostgreSQL driver/server.
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
