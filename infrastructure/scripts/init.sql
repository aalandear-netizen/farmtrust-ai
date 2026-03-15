-- FarmTrust AI – PostgreSQL initialization script
-- Enables PostGIS and TimescaleDB extensions

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Convert time-series tables to hypertables after they are created
-- (called by the application on startup via SQLAlchemy)
