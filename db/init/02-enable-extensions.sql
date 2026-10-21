-- Connect to primary yudhix database and enable cryptographic, UUID, and vector extensions
\c yudhix;

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Verify vector extension is functional
SELECT '[1,2,3]'::vector;
