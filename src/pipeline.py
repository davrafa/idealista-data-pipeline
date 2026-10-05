from curl_cffi import requests
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

# ORDEM OFICIAL DO ESQUEMA (Exatamente 38 colunas)
COLUMNS_ORDER = [
    "dbq_prd_type",          # 1
    "website_name",          # 2
    "competence_date",       # 3
    "listing_id",            # 4
    "listing_title",         # 5
    "listing_description",   # 6
    "property_type",         # 7
    "listing_type",          # 8
    "reference_market",      # 9
    "country_code",          # 10
    "location_description",  # 11
    "location_region",       # 12
    "location_province",     # 13
    "location_city",         # 14
    "location_zip",          # 15
    "locaiton_neighborhood", # 16 (Mantido o typo oficial do esquema)
    "location_street",       # 17
    "location_street_n",     # 18
    "location_lon",          # 19
    "location_lat",          # 20
    "area_unit",             # 21
    "area_value",            # 22
    "bedrooms",              # 23
    "bathrooms",             # 24
    "floor",                 # 25
    "total_floors",          # 26
    "amenities_list",        # 27
    "listing_date",          # 28
    "listing_status",        # 29
    "agent_id",              # 30
    "agent_url",             # 31
    "currency_code",         # 32
    "price",                 # 33
    "imageurl",              # 34
    "itemurl",               # 35
    "contract_id",           # 36
    "seller_id",             # 37
    "delivery_id"            # 38
]

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

def get_html_content(url="https://www.idealista.pt/comprar-casas/"):
    print(f"A tentar aceder ao Idealista (Modo Stealth): {url}")
    try:
        # impersonate="chrome110" disfarça o bot como se fosse um utilizador humano no Google Chrome
        resposta = requests.get(url, impersonate="chrome110", timeout=30)
        
        if resposta.status_code == 200:
            print("Página descarregada com sucesso!")
            return resposta.text
        else:
            print(f"O site bloqueou o acesso ou falhou. Erro HTTP: {resposta.status_code}")
            return ""
    except Exception as e:
        print(f"Erro ao tentar descarregar a página: {e}")
        return ""

def parse_listings(html: str):
    soup = BeautifulSoup(html, "html.parser")
    articles = soup.find_all("article")
    parsed_items = []
    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    
    # Gerar um delivery_id único em formato Unix Epoch (Timestamp)
    delivery_timestamp = str(datetime.utcnow().timestamp())

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

        title = link_el.get_text(strip=True) if link_el else "Imóvel Remax"
        href = link_el.get("href", "") if link_el else ""
        url = f"https://www.idealista.pt{href}" if href.startswith("/") else href

        price_val = 0.0
        price_match = re.search(r"([\d\.]+)\s*€", art.get_text())
        if price_match:
            clean_p = price_match.group(1).replace(".", "").strip()
            if clean_p.isdigit():
                price_val = float(clean_p)

        art_text = art.get_text(separator=" ")
        bedrooms = None
        typo_match = re.search(r"\bT(\d+)\b", art_text, re.IGNORECASE)
        if typo_match:
            bedrooms = int(typo_match.group(1))

        area_m2 = None
        area_match = re.search(r"(\d+)\s*m²", art_text)
        if area_match:
            area_m2 = float(area_match.group(1))

        prop_type = "Apartamento"
        if "moradia" in title.lower():
            prop_type = "Moradia"
        elif "duplex" in title.lower():
            prop_type = "Duplex"
        elif "terreno" in title.lower():
            prop_type = "Terreno"

        loc_desc = ""
        if "," in title:
            loc_desc = title.split(",")[-1].strip()

        img_tag = art.find("img")
        img_url = ""
        if img_tag:
            img_url = img_tag.get("src") or img_tag.get("data-ondemand-img") or ""

        parsed_items.append({
            "dbq_prd_type": "REAL-ESTATE-BASIC",
            "website_name": "Idealista",
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
            "itemurl": url,
            "contract_id": "recUat6mSQSsbwZzp",
            "seller_id": "AKIAS3CAQLRALQDSSYV2",
            "delivery_id": delivery_timestamp
        })

    return parsed_items

def save_to_postgres(items):
    conn = get_db_connection()
    cur = conn.cursor()

    # Apaga e recria para garantir a nova estrutura de 38 colunas
    cur.execute("DROP TABLE IF EXISTS real_estate.listings_export;")
    
    create_cols = []
    for col in COLUMNS_ORDER:
        if col in ["area_value", "price"]:
            create_cols.append(f"{col} NUMERIC")
        elif col in ["bedrooms", "bathrooms", "floor", "total_floors"]:
            create_cols.append(f"{col} INTEGER")
        elif col == "listing_id":
            create_cols.append(f"{col} TEXT PRIMARY KEY")
        else:
            create_cols.append(f"{col} TEXT")
            
    create_table_query = f"CREATE TABLE real_estate.listings_export ({', '.join(create_cols)});"
    cur.execute(create_table_query)

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
    print(f"Sucesso: {len(items)} registos persistidos.")

def export_to_delivery_file(output_file="data_file.txt"):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(f"SELECT {', '.join(COLUMNS_ORDER)} FROM real_estate.listings_export;")
    rows = cur.fetchall()

    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";", quoting=csv.QUOTE_ALL, lineterminator="\r\n")
        for row in rows:
            formatted_row = [str(val) if val is not None else "" for val in row]
            writer.writerow(formatted_row)

    cur.close()
    conn.close()
    print(f"Ficheiro gerado com sucesso! Contém exatamente {len(COLUMNS_ORDER)} colunas.")

if __name__ == "__main__":
    print("A iniciar pipeline local...")
    html_data = get_html_content()
    if html_data:
        data = parse_listings(html_data)
        if data:
            save_to_postgres(data)
            export_to_delivery_file()