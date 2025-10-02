# Retrieves Player Data from the Clash Royale API
'''
Author: Venom
Date: 2025-10-02
'''

import requests, sys, os
from Retrieve.b_process import BASE_URl, PLAYER_TAG, HEADERS


PLAYER_URL = f"{BASE_URl}/players/{PLAYER_TAG}"
PLAYER_BATTLE_LOG_URL = f"{BASE_URl}/players/{PLAYER_TAG}/battlelog"