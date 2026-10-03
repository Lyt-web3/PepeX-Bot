import requests

URL = "https://api.hyperliquid.xyz/info"
wallet = "0xbdbdeabcae1e56823fecfb4c8c994123d5b8d96f"

response = requests.post(URL, json={"type": "clearinghouseState", "user": wallet})
data = response.json()

print("Account value:", data["marginSummary"]["accountValue"])

for item in data["assetPositions"]:
    pos = item["position"]
    print(pos["coin"], "size:", pos["szi"], "entry:", pos["entryPx"], "uPnL:", pos["unrealizedPnl"])
import json
print(json.dumps(data, indent=2))