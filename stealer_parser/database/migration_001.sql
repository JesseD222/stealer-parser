-- Database migration script to update field sizes
-- Run this on existing databases to increase field limits

-- Increase username field size from 500 to 1000 characters
ALTER TABLE credentials ALTER COLUMN username TYPE VARCHAR(1000);

-- Add comment for tracking
COMMENT ON COLUMN credentials.username IS 'Increased to VARCHAR(1000) for better accommodation of long usernames';

-- Optional: You can also increase other fields if needed
-- ALTER TABLE credentials ALTER COLUMN software TYPE VARCHAR(500);
-- ALTER TABLE credentials ALTER COLUMN domain TYPE VARCHAR(500);

-- Show the updated table structure
\d credentials;