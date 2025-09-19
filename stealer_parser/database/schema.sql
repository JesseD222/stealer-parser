
-- Drop tables if they exist (in reverse order due to foreign key constraints)
DROP TABLE IF EXISTS cookies CASCADE;
DROP TABLE IF EXISTS credentials CASCADE;
DROP TABLE IF EXISTS systems CASCADE;
DROP TABLE IF EXISTS leaks CASCADE;

-- Table to store leak metadata
CREATE TABLE IF NOT EXISTS leaks (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    systems_count INTEGER DEFAULT 0
);

-- Table to store system information from compromised machines
CREATE TABLE IF NOT EXISTS systems (
    id SERIAL PRIMARY KEY,
    leak_id INTEGER NOT NULL REFERENCES leaks(id) ON DELETE CASCADE,
    machine_id VARCHAR(255),
    computer_name VARCHAR(255),
    hardware_id VARCHAR(255),
    machine_user VARCHAR(255),
    ip_address VARCHAR(255),  -- Supports both IPv4 and IPv6 addresses
    country VARCHAR(255),
    log_date VARCHAR(255),  -- Storing as string since format varies
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for systems table
CREATE INDEX IF NOT EXISTS idx_systems_leak_id ON systems(leak_id);
CREATE INDEX IF NOT EXISTS idx_systems_ip_address ON systems(ip_address);
CREATE INDEX IF NOT EXISTS idx_systems_computer_name ON systems(computer_name);

-- Table to store credentials extracted from compromised systems
CREATE TABLE IF NOT EXISTS credentials (
    id SERIAL PRIMARY KEY,
    system_id INTEGER NOT NULL REFERENCES systems(id) ON DELETE CASCADE,
    software VARCHAR(255),
    host TEXT,
    username VARCHAR(1000),
    password TEXT,
    domain VARCHAR(255),
    local_part VARCHAR(255),
    email_domain VARCHAR(255),
    filepath TEXT,
    stealer_name VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for credentials table
CREATE INDEX IF NOT EXISTS idx_credentials_system_id ON credentials(system_id);
CREATE INDEX IF NOT EXISTS idx_credentials_domain ON credentials(domain);
CREATE INDEX IF NOT EXISTS idx_credentials_email_domain ON credentials(email_domain);
CREATE INDEX IF NOT EXISTS idx_credentials_username ON credentials(username);
CREATE INDEX IF NOT EXISTS idx_credentials_stealer_name ON credentials(stealer_name);

-- Table to store browser cookies
CREATE TABLE IF NOT EXISTS cookies (
    id SERIAL PRIMARY KEY,
    system_id INTEGER NOT NULL REFERENCES systems(id) ON DELETE CASCADE,
    domain VARCHAR(255),
    domain_specified VARCHAR(255),
    path TEXT,
    secure VARCHAR(255),
    expiry VARCHAR(255),  -- Storing as string to handle various formats
    name VARCHAR(500),
    value TEXT,
    browser VARCHAR(255),
    profile VARCHAR(255),
    filepath TEXT,
    stealer_name VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for cookies table
CREATE INDEX IF NOT EXISTS idx_cookies_system_id ON cookies(system_id);
CREATE INDEX IF NOT EXISTS idx_cookies_domain ON cookies(domain);
CREATE INDEX IF NOT EXISTS idx_cookies_browser ON cookies(browser);
CREATE INDEX IF NOT EXISTS idx_cookies_stealer_name ON cookies(stealer_name);