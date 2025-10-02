# Retrieves War Data from a player's clan
'''
Author: Venom
Date: 2025-10-02
'''
import requests, sys, os
from Retrieve.b_process import BASE_URl, CLAN_TAG, HEADERS

WAR_URL = f"{BASE_URl}/clans/{CLAN_TAG}/currentwar"
