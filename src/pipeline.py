import re
import csv
from datetime import datetime
from curl_cffi import requests
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

def fetch_page(url: str) -> str:
    """Faz a requisição simulando um navegador Chrome real."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept-Language": "pt-PT,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    response = requests.get(url, headers=headers, impersonate="chrome120", timeout=15)
    if response.status_code == 200:
        return response.text
    print(f"Erro no pedido: Código {response.status_code}")
    return ""

def parse_listings(html: str):
    """Extrai os dados do HTML e formata segundo o schema REAL-ESTATE-BASIC."""
    soup = BeautifulSoup(html, "html.parser")
    articles = soup.find_all("article", class_="item")
    parsed_items = []

    for art in articles:
        prop_id = art.get("data-adid")
        if not prop_id:
            continue

        title_el = art.find("a", class_="item-link")
        title = title_el.text.strip() if title_el else "Sem título"
        url = "https://www.idealista.pt" + title_el["href"] if title_el and "href" in title_el.attrs else ""

        price_el = art.find("span", class_="item-price")
        price_val = 0.0
        if price_el:
            clean_price = re.sub(r"[^\d]", "", price_el.text)
            price_val = float(clean_price) if clean_price else 0.0

        details = [span.text.strip() for span in art.find_all("span", class_="item-detail")]
        typology = None
        area_m2 = None

        for d in details:
            if re.match(r"^T\d+", d, re.IGNORECASE):
                typology = d.upper()
            elif "m²" in d:
                match_area = re.search(r"(\d+)", d)
                if match_area:
                    area_m2 = int(match_area.group(1))

        location = "Portugal"
        if " em " in title:
            location = title.split(" em ")[-1].strip()

        parsed_items.append({
            "property_id": prop_id,
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
    print(f"Sucesso: {len(items)} registos inseridos/atualizados na base de dados.")

def export_to_csv(output_file="idealista_real_estate_basic.csv"):
    """Exporta diretamente da base de dados para o CSV exigido pelo Data Boutique."""
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
    print(f"Ficheiro {output_file} gerado com sucesso!")

if __name__ == "__main__":
    # Exemplo de recolha de páginas de listagem
    target_url = "https://www.idealista.pt/comprar-casas/lisboa/"
    print("A iniciar pipeline...")
    html_data = fetch_page(target_url)
    
    if html_data:
        data = parse_listings(html_data)
        if data:
            save_to_postgres(data)
            export_to_csv()
        else:
            print("Nenhum registo extraído. Verifica os seletores HTML.")
