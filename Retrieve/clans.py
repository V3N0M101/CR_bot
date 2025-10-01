import os, sys, requests
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor, as_completed, Future
from typing import Set, List, Optional, Tuple

# NOTE: Assuming your 'config.py' file exists relative to the script's path
# and contains the API_TOKEN variable.
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'API'))
try:
    from config import API_TOKEN
except ImportError:
    print("FATAL ERROR: Could not import API_TOKEN from config.py.")
    print("Please ensure config.py is in the correct directory and defines API_TOKEN.")
    sys.exit(1)


# --- CONFIGURATION ---
CLASH_API_BASE_URL = "https://api.clashroyale.com/v1"
HEADERS = {"Authorization": f"Bearer {API_TOKEN}"}
MAX_WORKERS = 10

# Variables (Customize these)

# 💡 Updated name based on your execution failure report
PLAYER_NAME_TO_FIND = "TS LUCAS XD" 
PLAYER_CLAN_NAME = "GDSJ 3"
TARGET_TROPHIES: Optional[int] = 10000 # Set to None to skip trophy check for standard ladder
# 💡 FIX: Setting this to None allows finding the player regardless of their POL rank, 
# ensuring the deck search proceeds.
TARGET_POL_TROPHIES: Optional[int] = 2000

# Constants for Battle Log Search
POL_TROPHY_THRESHOLD = 10000
# Based on debug output: 'pathOfLegend' in 'type' and 'Ranked1v1_NewArena2' in 'gameMode.name'
POL_GAME_MODES = ["ranked1v1", "pathoflegend", "ranked", "newarena2"] 
LADDER_GAME_MODES = ["ladder", "pvp", "pvp_a", "pvp_b"] # 'PvP' is often the standard ladder type


# ----------------------------------------------------------------
# Core API Interaction Functions
# ----------------------------------------------------------------

def get_clan_tags_by_name(clan_name: str) -> Set[str]:
    """Searches the Clash Royale API for clans matching the name."""
    encoded_name = quote(clan_name)
    url = f"{CLASH_API_BASE_URL}/clans?name={encoded_name}&limit=100"
    
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error finding clan '{clan_name}': {e}")
        return set()

    keywords = clan_name.lower().split() 
    
    # Filter for exact name match (case-insensitive and order-independent word presence)
    clan_tags = {
        clan["tag"].lstrip("#")
        for clan in data.get("items", [])
        if all(word in clan["name"].lower() for word in keywords)
    }
    
    return clan_tags

def fetch_clan_members(tag: str, player_name: str) -> List[str]:
    """Fetches members for a single clan tag and returns matching, stripped player tags."""
    clan_url = f"{CLASH_API_BASE_URL}/clans/%23{tag}"
    
    try:
        response = requests.get(clan_url, headers=HEADERS)
        response.raise_for_status()
        data = response.json()
        
        matching_player_tags = [
            member['tag'].lstrip("#")
            for member in data.get('memberList', [])
            if member['name'] == player_name
        ]
        return matching_player_tags

    except requests.exceptions.RequestException as e:
        print(f"Error getting members for clan #{tag}: {e}")
        return []

def check_player_trophies(tag: str, target_trophies: Optional[int], target_pol_trophies: Optional[int]) -> Optional[dict]:
    """
    Fetches player data and checks trophies. 
    Returns the player dict if criteria met or None otherwise.
    """
    player_url = f"{CLASH_API_BASE_URL}/players/%23{tag}"
    
    try:
        response = requests.get(player_url, headers=HEADERS)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching player data for tag #{tag}: {e}")
        return None

    trophy_match = True
    pol_trophy_match = True

    # Check standard trophies
    if target_trophies is not None and data.get('trophies', 0) < target_trophies:
        trophy_match = False

    # Check POL trophies
    if target_pol_trophies is not None:
        pol_trophies = data.get('currentPathOfLegendSeasonResult', {}).get('trophies')
        if pol_trophies is None or pol_trophies < target_pol_trophies:
            pol_trophy_match = False
            
    # If all non-None criteria pass, return the player data
    if trophy_match and pol_trophy_match:
        return data
    
    return None

# ----------------------------------------------------------------
# Search Orchestration
# ----------------------------------------------------------------

def search_and_verify_player(clan_tags: Set[str], player_name: str, target_trophies: Optional[int], target_pol_trophies: Optional[int]) -> Optional[dict]:
    """
    Coordinates concurrent search and verification with early exit upon match.
    Returns the found player data dictionary or None.
    """
    if not clan_tags:
        return None

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        clan_futures: List[Future] = []
        for tag in clan_tags:
            clan_futures.append(executor.submit(fetch_clan_members, tag, player_name))

        for clan_future in as_completed(clan_futures):
            try:
                player_tags = clan_future.result()
            except Exception as e:
                print(f"Error processing clan result: {e}")
                continue

            for player_tag in player_tags:
                player_future = executor.submit(check_player_trophies, player_tag, target_trophies, target_pol_trophies)
                player_data = player_future.result() 

                if player_data:
                    # 🚀 EARLY EXIT: Stop all pending jobs and return the match
                    print(f"🏆 Match found! Stopping search for remaining clans/players.")
                    executor.shutdown(wait=False, cancel_futures=True)
                    return player_data
                    
    return None

# ----------------------------------------------------------------
# Main Execution Block with Robust Deck Search
# ----------------------------------------------------------------

if __name__ == "__main__":
    print(f"Searching for clan: '{PLAYER_CLAN_NAME}'...")
    matching_clan_tags = get_clan_tags_by_name(PLAYER_CLAN_NAME)

    if not matching_clan_tags:
        print("No matching clans found. Exiting.")
        sys.exit(0)
        
    print(f"Found {len(matching_clan_tags)} clan tags.")

    # Format search criteria for output
    trophy_criteria_str = f"Trophy >= {TARGET_TROPHIES}" if TARGET_TROPHIES is not None else ""
    pol_criteria_str = f"POL >= {TARGET_POL_TROPHIES}" if TARGET_POL_TROPHIES is not None else ""
    criteria_list = [c for c in [trophy_criteria_str, pol_criteria_str] if c]
    criteria_str = " AND ".join(criteria_list) if criteria_list else " (no trophy criteria)"
    
    print(f"\nSearching for player: '{PLAYER_NAME_TO_FIND}' with criteria: {criteria_str} (in parallel)...")
    
    # 1. SEARCH FOR PLAYER AND VERIFY PROFILE TROPHIES
    found_player_data = search_and_verify_player(
        matching_clan_tags, 
        PLAYER_NAME_TO_FIND, 
        TARGET_TROPHIES, 
        TARGET_POL_TROPHIES
    )

    if not found_player_data:
        if TARGET_TROPHIES is None and TARGET_POL_TROPHIES is None:
            print(f"\n❌ Player '{PLAYER_NAME_TO_FIND}' was **NOT found** in the member lists of any searched clan.")
        else:
            print(f"\n❌ Player '{PLAYER_NAME_TO_FIND}' was found, but **no match met the required trophy criteria** in the searched clans.")
        sys.exit(0)

    # Variables from found player data
    player_trophies = found_player_data.get('trophies', 0)
    saved_tag = found_player_data['tag'].lstrip('#')
    
    # Print Player Summary
    print("\n" + "="*40)
    print("✅ PLAYER FOUND AND VERIFIED")
    print("="*40)
    print(f"Player Name: {found_player_data['name']}")
    print(f"Player Tag: #{saved_tag}")
    print(f"Trophy: {player_trophies}")
    
    pol_data = found_player_data.get('currentPathOfLegendSeasonResult', {})
    pol_trophies = pol_data.get('trophies', 'N/A')
    pol_league = pol_data.get('leagueNumber', 'N/A')
    
    print(f"POL Trophy: {pol_trophies}")
    print(f"POL League: {pol_league}")
    print("="*40)


    # 2. FETCH BATTLE LOG
    player_battle_url = f"{CLASH_API_BASE_URL}/players/%23{saved_tag}/battlelog"
    try:
        response = requests.get(player_battle_url, headers=HEADERS)
        response.raise_for_status()
        data = response.json() # data is now the list of battles
    except requests.exceptions.RequestException as e:
        print(f"Error fetching battle log: {e}")
        sys.exit(1)

    # --- DEBUG: Inspecting Recent Battle Modes ---
    print("\n--- DEBUG: Inspecting Recent Battle Modes ---")
    for i, battle in enumerate(data[:5]): # Check first 5 battles
        mode_name = battle.get('gameMode', {}).get('name', 'N/A')
        battle_type = battle.get('type', 'N/A')
        print(f"Battle {i+1} | Type: {battle_type} | Mode Name: {mode_name}")
        if i == 4:
            break
    print("-------------------------------------------\n")


    # --- 3. BATTLE SEARCH AND PRIORITIZED LOGIC (FIXED) ---
    
    A = None # Stores the specific player's data dictionary if found
    found_battle_type = None

    print(f"--- Starting Robust Battle Search ---")

    for battle in data:
        game_mode_name = battle.get('gameMode', {}).get('name', '').lower()
        battle_type = battle.get('type', '').lower()

        # 1. Determine if this battle qualifies based on priority:
        
        is_pol_or_ranked = (
            battle_type == 'pathoflegend' or 
            any(gm in game_mode_name for gm in POL_GAME_MODES)
        )
        
        is_standard_ladder = (
            battle_type == 'pvp' or 
            any(gm in game_mode_name for gm in LADDER_GAME_MODES)
        )

        qualifies_for_search = False
        
        # Priority 1: PoL/Ranked (if player is high trophy or the battle type explicitly is PoL)
        if player_trophies >= POL_TROPHY_THRESHOLD and is_pol_or_ranked:
            qualifies_for_search = True
            found_battle_type = f"PoL/Ranked ({battle_type} | {game_mode_name})"
        # Priority 2: Standard Ladder/PvP (Fallback)
        elif is_standard_ladder:
            qualifies_for_search = True
            found_battle_type = f"Standard Ladder ({battle_type} | {game_mode_name})"
            
        if not qualifies_for_search:
            continue # Skip to the next battle

        # 2. Find the player's data in either 'team' or 'opponent' lists:
        
        # CRUCIAL FIX: Combine team and opponent lists and search for the player's tag
        all_players_in_battle = battle.get('team', []) + battle.get('opponent', [])

        player_data_in_battle = next(
            (p for p in all_players_in_battle if p.get('tag', '').lstrip('#') == saved_tag), 
            None
        )

        # 3. If player data is found AND the battle qualifies, assign it and break:
        if player_data_in_battle:
            A = player_data_in_battle # A now holds the specific player's dictionary
            print(f"✅ Found matching player data in battle type: {found_battle_type}. Stopping search.")
            break
    
    # --- 4. CARD EXTRACTION AND FINAL OUTPUT ---
    
    extracted_cards = []

    if A:
        # A is the specific player's dictionary containing the cards
        cards_data = A.get('cards', []) 
        
        # Standard Level Calculation Logic
        MAX_STANDARD_LEVEL = 15
        for card in cards_data:
            current_level = card.get('level', 0)
            current_max_level = card.get('maxLevel', MAX_STANDARD_LEVEL)

            # Calculate the level offset (e.g., if max is 9, offset is 15-9=6)
            level_offset = MAX_STANDARD_LEVEL - current_max_level
            standardized_level = current_level + level_offset
            standardized_level = min(standardized_level, MAX_STANDARD_LEVEL)

            extracted_cards.append({
                'name': card.get('name'),
                'Level': standardized_level
            })
            
        print("\n" + "="*40)
        print(f"DECK FOUND in {found_battle_type}!")
        print("="*40)
        
        # Print the 8 cards
        for i in range(8):
            if i < len(extracted_cards):
                print(f"Card {i+1}: {extracted_cards[i]['name']} | Level = {extracted_cards[i]['Level']}")
            else:
                print(f"Card {i+1}: N/A") # Safety for incomplete deck
        print("="*40)

    else:
        print("\n❌ No deck found. No recent PoL or Ladder battle meeting the criteria was found in the battle log.")