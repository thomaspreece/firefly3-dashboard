"""
Helper script to list all Firefly III asset accounts and their IDs.
Run this locally to discover account IDs for account_config.py.

Usage:
    python list_accounts.py
"""
import os
from dotenv import load_dotenv
import requests

load_dotenv()

base = os.environ["FIREFLY_BASE_URL"].rstrip("/")
token = os.environ["FIREFLY_TOKEN"]
headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}

page = 1
accounts = []
while True:
    r = requests.get(
        f"{base}/api/v1/accounts",
        params={"type": "asset", "limit": 100, "page": page},
        headers=headers,
    )
    r.raise_for_status()
    data = r.json()
    accounts.extend(data["data"])
    if page >= data["meta"]["pagination"]["total_pages"]:
        break
    page += 1

print(f"{'ID':>5}  {'Name'}")
print("-" * 50)
for a in accounts:
    print(f"{a['id']:>5}  {a['attributes']['name']}")
