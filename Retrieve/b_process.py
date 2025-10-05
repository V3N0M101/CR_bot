# Processes all the API requests and returns the data in JSON format
'''
Author: Venom
Date: 2025-10-02
'''
### --- Imports --- ###
import requests, sys, os, datetime
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import Info
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'API'))
from API.config import API_TOKEN
import concurrent.futures
import threading

# Common Variables
BASE_URL = "https://proxy.royaleapi.dev/v1"
month = datetime.datetime.now().month 
year = datetime.datetime.now().year

# Add session as thread-local
thread_local = threading.local()

def get_session():
    if not hasattr(thread_local, 'session'):
        thread_local.session = requests.Session()
        thread_local.session.headers.update({"Authorization": f"Bearer {API_TOKEN}"})
    return thread_local.session

### --- Session Setup --- ###
session = requests.Session()
session.headers.update({"Authorization": f"Bearer {API_TOKEN}"})

### --- Clan Search --- ###
search_name = "%20".join(Info.CLAN_NAME.split())
CLAN_URL = f"{BASE_URL}/clans?name={search_name}&minScore={Info.MIN_SCORE}&limit={Info.LIMIT}"
response = session.get(CLAN_URL)
clan_data = response.json()
clans = clan_data.get("items", [])

# Filter clans to match exact case-sensitive name
clans = [clan for clan in clans if clan.get("name") == Info.CLAN_NAME]

### --- WAR FILTER --- ###
def WAR_FILTER(clan): return clan.get("warFrequency") != "never" and clan.get("clanWarTrophies", 0) >= Info.WAR_THRESHOLD

def get_filtered_clans(clans, war_true):
    """Filter clans based on war criteria."""
    if war_true:
        return [clan for clan in clans if WAR_FILTER(clan)]
    return []

def seasonal_clash(progress, current_month, current_year):
    """Get seasonal trophy data, falling back to previous months if needed."""
    seasonal_trophies = 10000
    
    # Try current month first, then fall back to previous months
    while seasonal_trophies == 10000 and current_month > 0:
        month_str = str(current_month).zfill(2)
        SEASONAL_URL = f"seasonal-trophy-road-{current_year}{month_str}"
        
        seasonal_arena_data = progress.get(SEASONAL_URL, {})
        seasonal_trophies = seasonal_arena_data.get("trophies", 0)
        
        if seasonal_trophies > 10000:
            break
            
        current_month -= 1
        
        if current_month == 0:
            current_month = 12
            current_year -= 1
            
        if (current_year < year - 1) or (current_year == year - 1 and current_month < month):
            break
    
    return seasonal_trophies

def check_member_fast(member_tag):
    """Fast member check with minimal data fetching."""
    session = get_session()
    
    PLAYER_URL = f"{BASE_URL}/players/{member_tag.replace('#', '%23')}"
    
    try:
        player_data = session.get(PLAYER_URL, timeout=3).json()
        
        name = player_data.get('name', '')
        if Info.PLAYER_NAME.lower() != name.lower():
            return None
        
        trophies = player_data.get('trophies', 0)
        player_pol = player_data.get('currentPathOfLegendSeasonResult', {}).get('trophies', 0)
        
        if trophies == 10000:
            progress = player_data.get('progress', {})
            seasonal_trophies = seasonal_clash(progress, month, year)
            player_trophies = seasonal_trophies
        else:
            player_trophies = trophies
        
        if player_trophies == Info.TROPHY or player_pol == Info.POL_TROPHY:
            return (name, member_tag, player_trophies, player_pol)
        
        return None
    except:
        return None

def player_search_parallel(clan):
    CLAN_TAG = clan.get("tag").replace("#", "%23")
    MEMBERS_URL = f"{BASE_URL}/clans/{CLAN_TAG}/members"
    
    try:
        members_data = session.get(MEMBERS_URL, timeout=3).json().get("items", [])
        member_tags = [member.get("tag") for member in members_data]
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
            future_to_tag = {executor.submit(check_member_fast, tag): tag for tag in member_tags}
            
            for future in concurrent.futures.as_completed(future_to_tag):
                result = future.result()
                if result:
                    for f in future_to_tag:
                        f.cancel()
                    return result
    except:
        pass
    
    return None, None, None, None

def main():
    if Info.CLAN_WAR_TRUE:
        filtered_clans = [clan for clan in clans if WAR_FILTER(clan)]
    else:
        filtered_clans = clans
    
    for clan in filtered_clans:
        print(f"Searching in Clan: {clan.get('name')} | Tag: {clan.get('tag')}")
        name, tag, trophies, pol = player_search_parallel(clan)
        if tag is not None:
            print(f"Player Found: {name} | Tag: {tag} | Trophies: {trophies} | PoL Trophies: {pol}")
            return
    
    print("Player Not Found")

if __name__ == "__main__":
    main()
