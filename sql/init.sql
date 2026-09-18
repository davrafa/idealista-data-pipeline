-- Criar esquema de trabalho
CREATE SCHEMA IF NOT EXISTS real_estate;

-- 1. Tabela Raw / Staging
CREATE TABLE IF NOT EXISTS real_estate.staging_idealista (
    id SERIAL PRIMARY KEY,
    raw_property_id VARCHAR(50),
    raw_title TEXT,
    raw_price VARCHAR(50),
    raw_typology VARCHAR(50),
    raw_area VARCHAR(50),
    raw_location TEXT,
    raw_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Tabela Analítica (Schema Oficial REAL-ESTATE-BASIC)
CREATE TABLE IF NOT EXISTS real_estate.listings_export (
    property_id VARCHAR(50) PRIMARY KEY,
    title TEXT NOT NULL,
    price NUMERIC(12, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'EUR',
    typology VARCHAR(10),
    area_m2 INT,
    location TEXT NOT NULL,
    url TEXT NOT NULL,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. View para validação e exportação limpa
CREATE OR REPLACE VIEW real_estate.v_real_estate_basic AS
SELECT 
    property_id,
    title,
    price,
    currency,
    typology,
    area_m2,
    location,
    url,
    TO_CHAR(scraped_at, 'YYYY-MM-DD HH24:MI:SS') AS scraped_at
FROM real_estate.listings_export;
