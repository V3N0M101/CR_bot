import requests, csv, os, sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'API'))
from config import API_TOKEN


url = "https://api.clashroyale.com/v1/cards"

headers = {"Authorization": f"Bearer {API_TOKEN}"}
response = requests.get(url, headers=headers)
data = response.json()

os.makedirs("./Data/images", exist_ok=True)

with open("./Data/cards.csv", "w", newline="", encoding="utf-8") as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(["Name", "Elixir", "Icon"])

    for card in data["items"]:
        name = card["name"]
        elixir = card.get("elixirCost", "N/A")
        icon_urls = card.get("iconUrls", {})

        for key in ["medium", "evolutionMedium"]:
            if key in icon_urls:
                safe_name = name.replace(" ", "_").replace(".", "").replace("/", "_")
                if key == "evolutionMedium":
                    filename = f"{safe_name}_evolution.png"
                    display_name = f"{safe_name}_Evolution"
                else:
                    filename = f"{safe_name}.png"
                    display_name = safe_name

                filepath = os.path.join("./Data/images", filename)

                if not os.path.isfile(filepath):
                    img_response = requests.get(icon_urls[key])
                    if img_response.status_code == 200:
                        with open(filepath, "wb") as f:
                            f.write(img_response.content)

                writer.writerow([display_name, elixir, filepath])

temp_file = "./Data/cards_sorted.csv"
sorted_file = "./Data/cards.csv"
with open("./Data/cards.csv", "r", encoding="utf-8", newline="") as infile:
    reader = csv.reader(infile)
    header = next(reader)
    rows = list(reader)
rows.sort(key=lambda x: x[0].lower())
with open(temp_file, "w", encoding="utf-8", newline="") as outfile:
    writer = csv.writer(outfile)
    writer.writerow(header)
    writer.writerows(rows)  
os.remove(sorted_file) 
os.rename(temp_file, sorted_file)      
print("Images retrieved, sorted and saved successfully")