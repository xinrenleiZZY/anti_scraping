import requests
resp = requests.get("http://localhost:50325/api/v1/browser/list")
print(resp.json())