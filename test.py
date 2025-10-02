import requests
from API.config import API_TOKEN

url = "https://api.clashroyale.com/v1/locations/global/pathoflegend/2025-08/rankings/players?limit=100000"
url2 = "https://api.clashroyale.com/v1/locations/57000047/rankings/players"
headers = {"Authorization": f"Bearer {API_TOKEN}"}

response = requests.get(url2, headers=headers)
print(response.status_code)
print(response.json())
