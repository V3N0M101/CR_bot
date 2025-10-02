# Processes all the API requests and returns the data in JSON format
'''
Author: Venom
Date: 2025-10-02
'''
### --- Imports --- ###
import requests, sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import Info
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'API'))
from API.config import API_TOKEN

# Common Variables
BASE_URl = "https://api.clashroyale.com/v1"

### --- Main Code --- ###
session = requests.Session()
session.headers.update({"Authorization": f"Bearer {API_TOKEN}"})

### --- Clan Search --- ###
search_name = "%20".join(Info.CLAN_NAME.split())
CLAN_URL = f"{BASE_URl}/clans?name={search_name}&minScore={Info.MIN_SCORE}&limit={Info.LIMIT}"
response = session.get(CLAN_URL)
clan_data = response.json()
clans = clan_data.get("items", [])
if Info.CLAN_WAR_TRUE:
    filtered_clans = [clan for clan in clans if clan.get("warFrequency") != "never" and clan.get("clanWarTrophies", 0) >= Info.WAR_THRESHOLD]
if filtered_clans:
    for clan in filtered_clans:
        print(f"Clan Name: {clan.get('name')}\n Tag: {clan.get('tag')}\n War Trophies: {clan.get('clanWarTrophies')}")
        CLAN_TAG = clan.get("tag").replace("#", "%23")
        