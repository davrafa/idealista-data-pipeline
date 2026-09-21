import os
import re
import csv
from datetime import datetime
from bs4 import BeautifulSoup
import psycopg2

DB_CONFIG = {
    "dbname": "realestate_db",
    "user": "data_engineer",
    "password": "secretpassword123",
    "host": "localhost",
    "port": "5433"
}

COLUMNS_ORDER = [
    "website_name", "competence_date", "listing_id", "listing_title", "listing_description",
    "property_type", "listing_type", "reference_market", "country_code", "location_description",
    "location_region", "location_province", "location_city", "location_zip", "locaiton_neighborhood",
    "location_street", "location_street_n", "location_lon", "location_lat", "area_unit",
    "area_value", "bedrooms", "bathrooms", "floor", "total_floors",
    "amenities_list", "listing_date", "listing_status", "agent_id", "agent_url",
    "currency_code", "price", "imageurl", "itemurl"
]

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

def get_html_content(filepath: str = "pagina.html") -> str:
    paths_to_check = [filepath, os.path.join("..", filepath), os.path.join(os.path.dirname(__file__), "..", filepath)]
    for path in paths_to_check:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
    return ""

def parse_listings(html: str):
    soup = BeautifulSoup(html, "html.parser")
    articles = soup.find_all("article")
    parsed_items = []
    today_str = datetime.utcnow().strftime("%Y-%m-%d")

    for idx, art in enumerate(articles, start=1):
        link_el = None
        prop_id = art.get("data-adid")

        for a in art.find_all("a", href=True):
            href = a["href"]
            match_id = re.search(r"/imovel/(\d+)", href)
            if match_id:
                prop_id = match_id.group(1)
                link_el = a
                break

        if not prop_id:
            continue

        # Título e URL
        title = link_el.get_text(strip=True) if link_el else "Imóvel Remax"
        href = link_el.get("href", "") if link_el else ""
        url = f"https://www.idealista.pt{href}" if href.startswith("/") else href

        # Preço
        price_val = 0.0
        price_match = re.search(r"([\d\.]+)\s*€", art.get_text())
        if price_match:
            clean_p = price_match.group(1).replace(".", "").strip()
            if clean_p.isdigit():
                price_val = float(clean_p)

        # Tipologia e Quartos
        art_text = art.get_text(separator=" ")
        bedrooms = None
        typo_match = re.search(r"\bT(\d+)\b", art_text, re.IGNORECASE)
        if typo_match:
            bedrooms = int(typo_match.group(1))

        # Área
        area_m2 = None
        area_match = re.search(r"(\d+)\s*m²", art_text)
        if area_match:
            area_m2 = float(area_match.group(1))

        # Tipo de Imóvel
        prop_type = "Apartamento"
        if "moradia" in title.lower():
            prop_type = "Moradia"
        elif "duplex" in title.lower():
            prop_type = "Duplex"
        elif "terreno" in title.lower():
            prop_type = "Terreno"

        # Localização
        loc_desc = ""
        if "," in title:
            loc_desc = title.split(",")[-1].strip()

        # Imagem primária
        img_tag = art.find("img")
        img_url = ""
        if img_tag:
            img_url = img_tag.get("src") or img_tag.get("data-ondemand-img") or ""

        parsed_items.append({
            "website_name": "idealista.pt",
            "competence_date": today_str,
            "listing_id": str(prop_id),
            "listing_title": title,
            "listing_description": "",
            "property_type": prop_type,
            "listing_type": "SALE",
            "reference_market": "RESIDENTIAL",
            "country_code": "PRT",
            "location_description": loc_desc,
            "location_region": "Lisboa",
            "location_province": "",
            "location_city": loc_desc,
            "location_zip": "",
            "locaiton_neighborhood": "",
            "location_street": "",
            "location_street_n": "",
            "location_lon": "",
            "location_lat": "",
            "area_unit": "SQMT",
            "area_value": area_m2,
            "bedrooms": bedrooms,
            "bathrooms": None,
            "floor": None,
            "total_floors": None,
            "amenities_list": "",
            "listing_date": "",
            "listing_status": "Available",
            "agent_id": "",
            "agent_url": "",
            "currency_code": "EUR",
            "price": price_val,
            "imageurl": img_url,
            "itemurl": url
        })

    return parsed_items

def save_to_postgres(items):
    conn = get_db_connection()
    cur = conn.cursor()

    cols = ", ".join(COLUMNS_ORDER)
    placeholders = ", ".join([f"%({col})s" for col in COLUMNS_ORDER])
    query = f"""
        INSERT INTO real_estate.listings_export ({cols})
        VALUES ({placeholders})
        ON CONFLICT (listing_id) DO UPDATE 
        SET price = EXCLUDED.price,
            competence_date = EXCLUDED.competence_date;
    """

    for item in items:
        cur.execute(query, item)

    conn.commit()
    cur.close()
    conn.close()
    print(f"Sucesso: {len(items)} registos persistidos no PostgreSQL.")

def export_to_delivery_file(output_file="data_file.txt"):
    """Gera o data_file.txt com as especificações estritas do Data Boutique."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(f"SELECT {', '.join(COLUMNS_ORDER)} FROM real_estate.listings_export;")
    rows = cur.fetchall()

    with open(output_file, "w", newline="", encoding="utf-8") as f:
        # Sem headers, delimitado por ;, todos os campos com aspas
        writer = csv.writer(f, delimiter=";", quoting=csv.QUOTE_ALL, lineterminator="\n")
        for row in rows:
            formatted_row = []
            for val in row:
                if val is None:
                    formatted_row.append("")
                else:
                    formatted_row.append(str(val))
            writer.writerow(formatted_row)

    cur.close()
    conn.close()
    print(f"Ficheiro de entrega '{output_file}' gerado com sucesso segundo as regras da plataforma!")

if __name__ == "__main__":
    print("A iniciar pipeline local...")
    html_data = get_html_content("pagina.html")
    if html_data:
        data = parse_listings(html_data)
        if data:
            save_to_postgres(data)
            export_to_delivery_file()