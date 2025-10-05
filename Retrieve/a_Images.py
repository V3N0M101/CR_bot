# Retrieves all the images from the Clash Royale API and saves them locally
'''
Author: Venom
Date: 2025-10-02
'''

import requests, os, sys, csv
from collections.abc import Mapping
from typing import Any
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'API'))
from config import API_TOKEN

URL: str = "https://proxy.royaleapi.dev/v1/cards"
HEADERS: Mapping[str, str] = {"Authorization": f"Bearer {API_TOKEN}"}
OUTPUT_DIR: str = "./Data"
IMAGES_DIR: str = os.path.join(OUTPUT_DIR, "images")
CARD_DATA_FILE: str = os.path.join(OUTPUT_DIR, "cards.csv")
TEMP_FILE: str = os.path.join(OUTPUT_DIR, "cards_sorted.csv")
CARD_CSV_HEADER: list[str] = ["Name", "Elixir", "Icon", "Ability Elixir"]
HARDCODED_CHAMPS: dict[str, int] = {
    "Little Prince": 3,
    "Monk": 1,
    "Boss Bandit": 1,
    "Archer Queen": 1,
    "Golden Knight": 1,
    "Skeleton King": 2,
    "Goblinstein": 2,
    "Mighty Miner": 1
}
ICON_KEYS: list[str] = ["medium", "evolutionMedium"]

def fetch_data(url: str, headers: Mapping[str, str]) -> dict[str, Any]:
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

def sanitize_name(name: str) -> str:
    return name.replace(" ", "_").replace(".", "").replace("/", "_")

def download_image(url: str, filepath: str) -> None:
    if not os.path.isfile(filepath):
        img_response = requests.get(url)
        img_response.raise_for_status()
        with open(filepath, "wb") as f:
            f.write(img_response.content)

def process_card_data(data: dict[str, Any]) -> list[list[Any]]:
    rows = []
    for card in data.get("items", []):
        name: str = card.get("name")
        if not name:
            continue
            
        elixir: Any = card.get("elixirCost", "N/A")
        rarity: str = card.get("rarity", "")
        icon_urls: dict[str, str] = card.get("iconUrls", {})
        safe_name: str = sanitize_name(name)
        ability_elixir = "N/A"
        if rarity.lower() == "champion":
            ability_elixir = HARDCODED_CHAMPS.get(name, "N/A")

        for key in ICON_KEYS:
            icon_url = icon_urls.get(key)
            if icon_url:
                if key == "evolutionMedium":
                    filename = f"{safe_name}_evolution.png"
                    display_name = f"{name} Evolution"
                else:
                    filename = f"{safe_name}.png"
                    display_name = name

                filepath: str = os.path.join(IMAGES_DIR, filename)
                
                try:
                    download_image(icon_url, filepath)
                    rows.append([display_name, elixir, filepath, ability_elixir])
                except requests.HTTPError as e:
                    print(f"Warning: Could not download image for {display_name} from {icon_url}. Error: {e}")
                except Exception as e:
                    print(f"Warning: An unexpected error occurred for {display_name}. Error: {e}")
                    
    return rows

def write_csv(filepath: str, header: list[str], rows: list[list[Any]]) -> None:
    with open(filepath, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(header)
        writer.writerows(rows)

def read_csv_data(filepath: str) -> tuple[list[str], list[list[Any]]]:
    with open(filepath, "r", encoding="utf-8", newline="") as infile:
        reader = csv.reader(infile)
        header = next(reader)
        rows = list(reader)
    return header, rows

def sort_and_save_csv(input_file: str, temp_file: str) -> None:
    header, rows = read_csv_data(input_file)
    rows.sort(key=lambda x: x[0].lower())
    write_csv(temp_file, header, rows)
    os.replace(temp_file, input_file)

try:
    data = fetch_data(URL, HEADERS)
    os.makedirs(IMAGES_DIR, exist_ok=True)
    
    card_rows = process_card_data(data)
    write_csv(CARD_DATA_FILE, CARD_CSV_HEADER, card_rows)

    sort_and_save_csv(CARD_DATA_FILE, TEMP_FILE)
    
    print("Images retrieved, sorted, and saved successfully")

except requests.HTTPError as e:
    print(f"Error fetching data or image: {e}")
except Exception as e:
    print(f"An unexpected error occurred: {e}")