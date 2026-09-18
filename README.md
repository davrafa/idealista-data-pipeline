# idealista-data-pipeline
Automated data pipeline, PostgreSQL storage, and schema mapping for Portuguese real estate data.
# Idealista Real Estate Data Pipeline

Pipeline automatizada para extração, validação e estruturação de dados imobiliários de Portugal (PRT), com carregamento em base de dados PostgreSQL e exportação no schema `REAL-ESTATE-BASIC`.

## Arquitetura
- **Ingestão:** Python / Web Scraping (extração de atributos em HTML)
- **Armazenamento Staging:** PostgreSQL em container Docker
- **Validação & Exportação:** Transformação SQL/Pydantic para formato tabular compatível com o marketplace

## Data Dictionary & Schema Mapping (`REAL-ESTATE-BASIC`)

| Field Name | Source on Website | Type | Transformation Rule |
| :--- | :--- | :--- | :--- |
| `property_id` | `data-adid` attribute | String | Extracted as unique listing identifier |
| `title` | Tag `a.item-link` text | String | Clean whitespace, trim |
| `price` | `.price-row .item-price` | Float | Stripped `€` currency symbol and commas |
| `currency` | Hardcoded value | String | Standardized to `EUR` |
| `typology` | Listing detail bullet | String | Normalized pattern (e.g., T0, T1, T2, T3) |
| `area_m2` | Listing details (`m²`) | Integer | Parsed integer before area unit |
| `location` | Header location text | String | Standardized locality name |
| `url` | Listing `href` link | String | Canonical URL path |
| `scraped_at` | System execution clock | Timestamp | UTC format `YYYY-MM-DD HH:MM:SS` |
