# file: check_zoom_token.py
import os
import sys
import requests

env_token = os.getenv("ZOOM_ACCESS_TOKEN")
cli_token = sys.argv[1] if len(sys.argv) > 1 else None
token = cli_token or env_token

if not token:
    print("Set ZOOM_ACCESS_TOKEN env var or pass token as first argument.")
    sys.exit(1)

headers = {"Authorization": f"Bearer {token}"}

resp = requests.get("https://api.zoom.us/v2/users/me", headers=headers, timeout=10)

print(f"Status: {resp.status_code}")
if resp.ok:
    data = resp.json()
    print(f"Valid token. User: {data.get('email')} (id: {data.get('id')})")
else:
    print("Token invalid or expired:", resp.text)