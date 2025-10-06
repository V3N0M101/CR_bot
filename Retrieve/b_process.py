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
def get_clans():
    search_name = "%20".join(Info.CLAN_NAME.split())
    CLAN_URL = f"{BASE_URL}/clans?name={search_name}&minScore={Info.MIN_SCORE}&limit={Info.LIMIT}"
    response = session.get(CLAN_URL)
    clan_data = response.json()
    clans = clan_data.get("items", [])
    return [clan for clan in clans if clan.get("name") == Info.CLAN_NAME]

### --- WAR FILTER --- ###
def get_war_trophy_range(threshold):
    if threshold >= 5000:
        return (5000, float('inf'))
    elif threshold >= 4000:
        return (4000, 5000)
    elif threshold >= 3000:
        return (3000, 4000)
    elif threshold >= 2000:
        return (2000, 3000)
    elif threshold >= 1000:
        return (1000, 2000)
    else:
        return (threshold, 1000)

def WAR_FILTER(clan):
    clan_war_trophies = clan.get("clanWarTrophies", 0)
    min_range, max_range = get_war_trophy_range(Info.WAR_THRESHOLD)
    return min_range <= clan_war_trophies < max_range

def seasonal_clash(progress, current_month, current_year):
    seasonal_trophies = 10000
    
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

def display_deck_info(battle_data, deck_counter=None):
    cards = battle_data.get('team')[0].get('cards')
    
    for i, card in enumerate(cards):
        Max = card.get('maxLevel')
        Difference = 14 - Max
        Current_card_Level = card.get('level') + Difference
        card_number = (i % 8) + 1
        
        if Info.CLAN_WAR_TRUE and i % 8 == 0:
            if deck_counter is not None:
                deck_number = deck_counter[0] + (i // 8)
            else:
                deck_number = (i // 8) + 1
            print(f"\n--- DECK{deck_number} ---\n")
        
        print(f"Card {card_number}: {card.get('name')} | Level {Current_card_Level}")
    
    if Info.CLAN_WAR_TRUE and deck_counter is not None:
        num_decks = (len(cards) + 7) // 8
        deck_counter[0] += num_decks
    
    if not Info.CLAN_WAR_TRUE:
        tower_data = battle_data.get('team')[0].get('supportCards')[0]
        tower = tower_data.get('name')
        Max = tower_data.get('maxLevel')
        Difference = 14 - Max
        tower_level = tower_data.get('level') + Difference
        print(f"\nTower: {tower} | Level {tower_level}")

def print_clan_search_info(filtered_clans):
    if filtered_clans:
        min_range, max_range = get_war_trophy_range(Info.WAR_THRESHOLD)
        if max_range == float('inf'):
            print(f"Searching clans in war trophy range: {min_range}+")
        else:
            print(f"Searching clans in war trophy range: {min_range}-{max_range}")

def player_search(filtered_clans):
    for clan in filtered_clans:
        print(f"Searching in Clan: {clan.get('name')} | Tag: {clan.get('tag')} | War Trophies: {clan.get('clanWarTrophies', 0)}")
        name, tag, trophies, pol = player_search_parallel(clan)
        if tag is not None:
            print(f"\nPlayer Found: {name} | Tag: {tag} | Trophies: {trophies} | PoL Trophies: {pol}\n")
            return tag
    print("Player Not Found")
    return None

def process_clan_war_battles(battles_data):
    print(f"\033[0;36m### --- CLAN_WAR_DECKS --- ###\033[0m")
    
    war_battles = [b for b in battles_data if b.get('type') in ['riverRaceDuelColosseum', 'riverRacePvP']]
    
    if not war_battles:
        print(f"\n\033[0;31mNo clan war battles found\033[0m\n")
        print(f"Last battle type: {battles_data[0].get('type')}\n")
        display_deck_info(battles_data[0])
        return
    
    deck_counter = [1]
    for battle in war_battles:
        display_deck_info(battle, deck_counter)

def process_regular_battles(battles_data):
    print(f"\033[0;36m### --- PLAYER_DECK --- ###\033[0m")
    
    for i, battle in enumerate(battles_data):
        battle_type = battle.get('type')
        
        if Info.POL_TRUE:
            if battle_type == 'pathOfLegend':
                display_deck_info(battle)
                return
        elif battle_type in ['pvp', 'trail']:
            display_deck_info(battle)
            return
        
        if i == len(battles_data) - 1:
            print(f"\n\033[0;31mThe specific battle type was not found\033[0m\n")
            print(f"Last battle type: {battle_type}\n")
            display_deck_info(battle)

def get_battle_data(player_tag):
    BATTLE_URL = f"{BASE_URL}/players/{player_tag.replace('#', '%23')}/battlelog"
    try:
        return session.get(BATTLE_URL).json()
    except Exception as e:
        print(f"Error fetching battles: {e}")
        return None

def main():
    clans = get_clans()
    
    if Info.CLAN_WAR_TRUE:
        filtered_clans = [clan for clan in clans if WAR_FILTER(clan)]
        print_clan_search_info(filtered_clans)
    else:
        filtered_clans = clans
    
    player_tag = player_search(filtered_clans)
    if player_tag is None:
        return
    
    battles_data = get_battle_data(player_tag)
    if battles_data is None:
        return

    if Info.CLAN_WAR_TRUE:
        process_clan_war_battles(battles_data)
    else:
        process_regular_battles(battles_data)

if __name__ == "__main__":
    main()
