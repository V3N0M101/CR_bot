import os
import sys
import requests
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Set, List, Optional, Dict, Any, Tuple

# === ENVIRONMENT SETUP ===
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'API'))
try:
    from config import API_TOKEN
except ImportError:
    print("FATAL: Missing 'config.py' or API_TOKEN. Check 'API' directory.")
    sys.exit(1)

# === CONFIGURATION ===
API_BASE_URL = "https://api.clashroyale.com/v1"
HEADERS = {"Authorization": f"Bearer {API_TOKEN}"}
MAX_WORKERS = 10

# --- USER VARIABLES ---
# NOTE: This name is now used for display only, as the primary search is by TROPHIES/CLAN
PLAYER_NAME_TO_FIND = "Youtube JUNE" 
PLAYER_CLAN_NAME = "KOREA"
# Set to None to skip the check
TARGET_TROPHIES: Optional[int] = 10000 
TARGET_POL_TROPHIES: Optional[int] = 2221

# --- CONSTANTS ---
POL_TROPHY_THRESHOLD = 10000
POL_GAME_MODES = ["ranked1v1", "pathoflegend", "ranked", "newarena2"] 
LADDER_GAME_MODES = ["ladder", "pvp", "pvp_a", "pvp_b"]
MAX_CARD_LEVEL = 15

# ================================================================
# PLAYER FINDER CLASS
# ================================================================

class PlayerFinder:
    """Encapsulates logic for finding a player who meets trophy requirements within target clans."""

    def __init__(self, name_hint: str, clan_name: str, trophies: Optional[int], pol_trophies: Optional[int]):
        # name_hint is now primarily used for logging/display
        self.name_hint = name_hint 
        self.clan_name = clan_name
        self.target_trophies = trophies
        self.target_pol_trophies = pol_trophies
        self.found_player_data: Optional[Dict[str, Any]] = None

    # --- API HELPER METHODS ---

    def _get_clan_tags(self) -> Set[str]:
        """Fetches tags of clans matching the name."""
        encoded_name = quote(self.clan_name)
        url = f"{API_BASE_URL}/clans?name={encoded_name}&limit=100"
        
        try:
            response = requests.get(url, headers=HEADERS)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            print(f"API Error finding clan '{self.clan_name}': {e}")
            return set()

        keywords = self.clan_name.lower().split() 
        return {
            clan["tag"].lstrip("#")
            for clan in data.get("items", [])
            if all(word in clan["name"].lower() for word in keywords)
        }

    def _fetch_clan_members(self, tag: str) -> List[str]:
        """
        Fetches members for a single clan tag, returning ALL player tags.
        (Name filtering removed to meet new requirement.)
        """
        clan_url = f"{API_BASE_URL}/clans/%23{tag}"
        try:
            response = requests.get(clan_url, headers=HEADERS)
            response.raise_for_status()
            data = response.json()
            
            # Returns ALL member tags
            return [
                member['tag'].lstrip("#")
                for member in data.get('memberList', [])
            ]
        except requests.exceptions.RequestException:
            return []

    def _check_player_profile(self, tag: str) -> Optional[Dict[str, Any]]:
        """
        Fetches player data and checks both standard and PoL trophy criteria.
        Returns player data only if ALL criteria are met.
        """
        player_url = f"{API_BASE_URL}/players/%23{tag}"
        try:
            response = requests.get(player_url, headers=HEADERS)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException:
            return None

        # Standard Trophies check
        if (self.target_trophies is not None and 
            data.get('trophies', 0) < self.target_trophies):
            return None

        # POL Trophies check
        if self.target_pol_trophies is not None:
            pol_trophies = data.get('currentPathOfLegendSeasonResult', {}).get('trophies')
            if pol_trophies is None or pol_trophies < self.target_pol_trophies:
                return None
            
        # Player qualifies based on trophy criteria
        return data

    # --- ORCHESTRATION ---

    def search(self) -> bool:
        """Coordinates the concurrent search for any player meeting trophy criteria."""
        print(f"Searching for clan: '{self.clan_name}'...")
        clan_tags = self._get_clan_tags()

        if not clan_tags:
            print("FAIL: No matching clans found.")
            return False
            
        print(f"Found {len(clan_tags)} clan tags to check.")

        player_tags_to_check: Set[str] = set()
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            
            # Step 1: Concurrently fetch ALL member tags from matching clans
            clan_futures = [executor.submit(self._fetch_clan_members, tag) for tag in clan_tags]
            
            for future in as_completed(clan_futures):
                # All tags are added since we removed the name filter
                player_tags_to_check.update(future.result())

            if not player_tags_to_check:
                 print(f"No members found in any matching clan member list.")
                 return False
            
            print(f"Checking {len(player_tags_to_check)} player profiles for trophy criteria...")

            # Step 2: Concurrently check player profiles for trophies and details
            player_futures = [executor.submit(self._check_player_profile, tag) 
                              for tag in player_tags_to_check]

            for future in as_completed(player_futures):
                player_data = future.result()
                if player_data:
                    self.found_player_data = player_data
                    print("🏆 Match found! Stopping parallel search.")
                    executor.shutdown(wait=False, cancel_futures=True) # Early exit
                    return True

        return False # Returns False if no player passed the trophy check

    # --- DECK EXTRACTION ---

    def _fetch_battle_log(self, tag: str) -> Optional[List[Dict[str, Any]]]:
        """Fetches the battle log for a player tag."""
        player_battle_url = f"{API_BASE_URL}/players/%23{tag}/battlelog"
        try:
            response = requests.get(player_battle_url, headers=HEADERS)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"API Error fetching battle log: {e}")
            return None

    def get_deck(self) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
        """Searches the battle log for the most recent qualifying battle deck."""
        if not self.found_player_data:
            return None, None
        
        tag = self.found_player_data['tag'].lstrip('#')
        trophies = self.found_player_data.get('trophies', 0)
        battle_log = self._fetch_battle_log(tag)
        
        if not battle_log:
            return None, None

        for battle in battle_log:
            game_mode_name = battle.get('gameMode', {}).get('name', '').lower()
            battle_type = battle.get('type', '').lower()

            is_pol_or_ranked = (battle_type == 'pathoflegend' or 
                                any(gm in game_mode_name for gm in POL_GAME_MODES))
            is_standard_ladder = (battle_type == 'pvp' or 
                                  any(gm in game_mode_name for gm in LADDER_GAME_MODES))

            qualifies_for_search = False
            found_type = "N/A"
            
            # Priority 1: PoL/Ranked 
            if trophies >= POL_TROPHY_THRESHOLD and is_pol_or_ranked:
                qualifies_for_search = True
                found_type = f"PoL/Ranked ({battle_type} | {game_mode_name})"
            # Priority 2: Standard Ladder/PvP
            elif is_standard_ladder:
                qualifies_for_search = True
                found_type = f"Standard Ladder ({battle_type} | {game_mode_name})"
                
            if not qualifies_for_search:
                continue

            # Find the player's data
            all_players_in_battle = battle.get('team', []) + battle.get('opponent', [])
            player_data_in_battle = next(
                (p for p in all_players_in_battle if p.get('tag', '').lstrip('#') == tag), 
                None
            )

            if player_data_in_battle and player_data_in_battle.get('cards'):
                return self._standardize_deck_levels(player_data_in_battle['cards']), found_type
        
        return None, None

    def _standardize_deck_levels(self, cards_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Converts card levels to the standard max level (Level 15)."""
        extracted_cards = []
        for card in cards_data:
            current_level = card.get('level', 0)
            current_max_level = card.get('maxLevel', MAX_CARD_LEVEL)
            
            standardized_level = min(current_level + (MAX_CARD_LEVEL - current_max_level), MAX_CARD_LEVEL)

            extracted_cards.append({
                'name': card.get('name'),
                'Level': standardized_level
            })
        return extracted_cards

# ================================================================
# MAIN EXECUTION
# ================================================================

def main():
    finder = PlayerFinder(PLAYER_NAME_TO_FIND, PLAYER_CLAN_NAME, TARGET_TROPHIES, TARGET_POL_TROPHIES)
    
    # Format criteria for printing
    trophy_criteria_str = (f"Trophy $\\ge$ {TARGET_TROPHIES}" if TARGET_TROPHIES is not None else "")
    pol_criteria_str = (f"POL $\\ge$ {TARGET_POL_TROPHIES}" if TARGET_POL_TROPHIES is not None else "")
    criteria_list = [c for c in [trophy_criteria_str, pol_criteria_str] if c]
    criteria_str = " AND ".join(criteria_list) if criteria_list else "(no trophy criteria)"
    
    print(f"\nSearching for ANY player in '{PLAYER_CLAN_NAME}' with criteria: {criteria_str}...")

    # 1. SEARCH AND VERIFY PLAYER (Trophies only)
    if not finder.search():
        print(f"\nFAIL: No player found in the clans who meets the trophy criteria.")
        # Mentioning the original name is irrelevant now
        sys.exit(0)

    # 2. DISPLAY PLAYER SUMMARY
    player_data = finder.found_player_data
    saved_tag = player_data['tag'].lstrip('#')
    pol_data = player_data.get('currentPathOfLegendSeasonResult', {})

    print("\n" + "="*40)
    print("✅ PLAYER FOUND AND VERIFIED")
    print("="*40)
    print(f"Name: {player_data['name']}")
    print(f"Tag: #{saved_tag}")
    print(f"Trophy: {player_data.get('trophies', 'N/A')}")
    print(f"POL Trophy: {pol_data.get('trophies', 'N/A')}")
    print(f"POL League: {pol_data.get('leagueNumber', 'N/A')}")
    print("="*40)

    # 3. FETCH AND EXTRACT DECK
    print("\n--- Fetching Battle Log and Extracting Deck ---")
    extracted_deck, found_type = finder.get_deck()

    if extracted_deck:
        print("\n" + "="*40)
        print(f"DECK FOUND in {found_type}!")
        print("="*40)
        
        for i in range(8):
            if i < len(extracted_deck):
                card = extracted_deck[i]
                print(f"Card {i+1}: {card['name']} | Level = {card['Level']}")
            else:
                print(f"Card {i+1}: N/A (Deck incomplete)") 
        print("="*40)
    else:
        print("\nFAIL: No deck found. No qualifying PoL or Ladder battle was in the recent log for this player.")


if __name__ == "__main__":
    main()