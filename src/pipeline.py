import os
import re
import csv
from datetime import datetime
from bs4 import BeautifulSoup
import psycopg2

# Configuração da Base de Dados (PostgreSQL no Docker)
DB_CONFIG = {
    "dbname": "realestate_db",
    "user": "data_engineer",
    "password": "secretpassword123",
    "host": "localhost",
    "port": "5432"
}

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

def get_html_content(filepath: str = "pagina.html") -> str:
    """Lê o HTML local guardado pelo navegador."""
    paths_to_check = [
        filepath,
        os.path.join("..", filepath),
        os.path.join(os.path.dirname(__file__), "..", filepath)
    ]
    for path in paths_to_check:
        if os.path.exists(path):
            print(f"A carregar dados locais de {path}...")
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
    
    print(f"Ficheiro {filepath} não encontrado.")
    return ""

def parse_listings(html: str):
    """Extrai os 30 anúncios formatados no schema REAL-ESTATE-BASIC."""
    soup = BeautifulSoup(html, "html.parser")
    articles = soup.find_all("article")
    parsed_items = []

    print(f"A analisar {len(articles)} blocos de anúncios encontrados...")

    for idx, art in enumerate(articles, start=1):
        # 1. Obter Link e ID da propriedade
        link_el = None
        prop_id = art.get("data-adid")

        # Procura link que aponte para o imóvel (/imovel/...)
        for a in art.find_all("a", href=True):
            href = a["href"]
            match_id = re.search(r"/imovel/(\d+)", href)
            if match_id:
                prop_id = match_id.group(1)
                link_el = a
                break

        # Fallback de ID se não estiver explícito no href
        if not prop_id:
            prop_id = f"remax_temp_{idx}"

        # 2. Título e URL
        title = "Imóvel Remax"
        url = "https://www.idealista.pt"
        if link_el:
            raw_title = link_el.get_text(strip=True)
            if raw_title:
                title = raw_title
            href = link_el.get("href", "")
            url = f"https://www.idealista.pt{href}" if href.startswith("/") else href
        else:
            first_a = art.find("a", href=True)
            if first_a:
                url = first_a["href"]
                title = first_a.get_text(strip=True) or title

        # 3. Preço
        price_val = 0.0
        # Procura por padrões monetários no texto do artigo (ex: 975.000 €)
        price_match = re.search(r"([\d\.]+)\s*€", art.get_text())
        if price_match:
            clean_price = price_match.group(1).replace(".", "").strip()
            if clean_price.isdigit():
                price_val = float(clean_price)

        # 4. Tipologia e Área
        art_text = art.get_text(separator=" ")
        
        # Tipologia (T0, T1, T2, T3, etc.)
        typology = None
        typo_match = re.search(r"\b(T\d+)\b", art_text, re.IGNORECASE)
        if typo_match:
            typology = typo_match.group(1).upper()

        # Área (ex: 139 m²)
        area_m2 = None
        area_match = re.search(r"(\d+)\s*m²", art_text)
        if area_match:
            area_m2 = int(area_match.group(1))

        # 5. Localização
        location = "Portugal"
        if " em " in title:
            location = title.split(" em ")[-1].strip()

        parsed_items.append({
            "property_id": str(prop_id),
            "title": title,
            "price": price_val,
            "currency": "EUR",
            "typology": typology,
            "area_m2": area_m2,
            "location": location,
            "url": url,
            "scraped_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        })

    return parsed_items

def save_to_postgres(items):
    """Guarda os dados transformados no PostgreSQL com upsert."""
    conn = get_db_connection()
    cur = conn.cursor()

    query = """
        INSERT INTO real_estate.listings_export 
        (property_id, title, price, currency, typology, area_m2, location, url, scraped_at)
        VALUES (%(property_id)s, %(title)s, %(price)s, %(currency)s, %(typology)s, %(area_m2)s, %(location)s, %(url)s, %(scraped_at)s)
        ON CONFLICT (property_id) DO UPDATE 
        SET price = EXCLUDED.price,
            scraped_at = EXCLUDED.scraped_at;
    """

    for item in items:
        cur.execute(query, item)

    conn.commit()
    cur.close()
    conn.close()
    print(f"Sucesso: {len(items)} registos persistidos no PostgreSQL.")

def export_to_csv(output_file="idealista_real_estate_basic.csv"):
    """Exporta diretamente da view SQL para o CSV oficial exigido pelo marketplace."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM real_estate.v_real_estate_basic;")
    
    rows = cur.fetchall()
    col_names = [desc[0] for desc in cur.description]

    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(col_names)
        writer.writerows(rows)

    cur.close()
    conn.close()
    print(f"Ficheiro '{output_file}' gerado com sucesso!")

if __name__ == "__main__":
    print("A iniciar pipeline local...")
    html_data = get_html_content("pagina.html")
    
    if html_data:
        data = parse_listings(html_data)
        if data:
            save_to_postgres(data)
            export_to_csv()
        else:
            print("Nenhum dado pôde ser extraído.")