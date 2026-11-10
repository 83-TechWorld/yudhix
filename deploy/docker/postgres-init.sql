-- Runs once, on an empty data volume. The API creates its own schema on startup;
-- Keycloak only needs its database to exist.
CREATE DATABASE keycloak OWNER yudhix;
