import requests
from bs4 import BeautifulSoup
import json
import os
import time
import re
import sys

# Add parent directory to path for Info import
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import Info

class RoyaleAPIScraper:
    def __init__(self):
        self.base_url = "https://royaleapi.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def get_page(self, url, delay=1):
        """Get page content with rate limiting."""
        # TODO: Add your request logic here
        # - Add delay
        # - Make request
        # - Return BeautifulSoup object
        pass
    
    def search_players_by_name(self, player_name=None):
        """Search for players using the search results page."""
        if player_name is None:
            player_name = Info.PLAYER_NAME
        
        # TODO: Build search URL
        search_url = f"{self.base_url}/player/search/results"
        params = {'q': player_name, 'fwd': '1'}
        
        # TODO: Get search page
        # TODO: Find all player links on the page
        # TODO: Extract player tags from links
        # TODO: Return list of player tags
        
        players_found = []
        return players_found
    
    def scrape_player_profile(self, player_tag):
        """Scrape detailed player profile data."""
        # TODO: Clean player tag (remove # if present)
        # TODO: Build player profile URL
        # TODO: Get player page
        # TODO: Extract player data:
        #   - name
        #   - trophies
        #   - pol_trophies
        #   - level
        #   - clan info (name and tag)
        
        player_data = {
            'tag': f"#{player_tag}",
            'name': None,
            'trophies': None,
            'pol_trophies': None,
            'level': None,
            'clan': None  # {'name': '', 'tag': ''} or None
        }
        
        return player_data
    
    def validate_player_match(self, player_data):
        """Validate if player matches Info.py criteria."""
        # TODO: Check name match (case insensitive)
        # TODO: Check trophy match based on Info.POL_TRUE:
        #   - If POL_TRUE: check pol_trophies against Info.POL_TROPHY
        #   - If not POL_TRUE: check trophies against Info.TROPHY
        # TODO: Check clan match:
        #   - If Info.CLAN_NAME exists: player must be in that exact clan
        #   - If Info.CLAN_NAME is empty: player must not be in any clan
        
        # Return (True, "success message") or (False, "reason for failure")
        return False, "Not implemented yet"
    
    def find_matching_player(self):
        """Main function to find player matching Info.py criteria."""
        print("=" * 60)
        print("PLAYER SEARCH - Info.py Configuration:")
        print(f"Target Player: '{Info.PLAYER_NAME}'")
        print(f"Target Clan: '{Info.CLAN_NAME}'" if Info.CLAN_NAME else "No Clan Required")
        print(f"PoL Mode: {Info.POL_TRUE}")
        print("=" * 60)
        
        # TODO: Search for players by name
        # TODO: Loop through each found player
        # TODO: Scrape detailed data for each player
        # TODO: Validate each player against criteria
        # TODO: Return first matching player or None
        
        return None
    
    def save_to_json(self, data, filename):
        """Save data to JSON file."""
        # TODO: Create directory if it doesn't exist
        # TODO: Save data to JSON file
        # TODO: Print success message
        pass
    
    def debug_save_html(self, soup, filename):
        """Save HTML content for debugging."""
        # TODO: Save BeautifulSoup content to file for inspection
        pass

def main():
    scraper = RoyaleAPIScraper()
    
    # TODO: Call find_matching_player()
    # TODO: If player found, display results and save to JSON
    # TODO: If not found, display failure message
    
    print("Template ready - implement the TODO sections!")

if __name__ == "__main__":
    main()

# HELPFUL HINTS:
# 
# 1. Search URL format: https://royaleapi.com/player/search/results?q={name}&fwd=1
# 2. Player profile URL: https://royaleapi.com/player/{tag_without_hash}
# 3. Look for links with href containing "/player/" to find player tags
# 4. Use regex patterns to extract numbers from text for trophies
# 5. BeautifulSoup selectors: soup.find(), soup.select(), soup.get_text()
# 6. Always add delays between requests to be respectful
# 7. Save HTML to files for debugging when selectors don't work
# 8. Regular trophies vs PoL trophies are usually displayed differently on the page
# 9. Clan links have href containing "/clan/"
# 10. Use try/except blocks for robust error handling