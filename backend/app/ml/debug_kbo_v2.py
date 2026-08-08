import os
import httpx
import json
from datetime import date, timedelta

API_SPORTS_KEY = os.environ.get("API_SPORTS_KEY", "721b2f330a081784fcd13aa87d87063b")
API_SPORTS_BASE = "https://v1.baseball.api-sports.io"
LEAGUE_ID = 5  # KBO, confirmado en el paso anterior

target_date = date.today() + timedelta(days=1)
date_str = target_date.strftime("%Y-%m-%d")
season = target_date.year

print(f"Buscando partidos KBO: league={LEAGUE_ID} season={season} date={date_str}")
print("=" * 60)

with httpx.Client(timeout=10.0) as client:
    resp = client.get(
        f"{API_SPORTS_BASE}/games",
        headers={"x-apisports-key": API_SPORTS_KEY},
        params={"league": LEAGUE_ID, "season": season, "date": date_str},
    )
    print(f"Status HTTP: {resp.status_code}")
    data = resp.json()
    print(f"errors: {data.get('errors')}")
    print(f"results: {data.get('results')}")
    print("\nJSON crudo (primeros 3000 chars):")
    print(json.dumps(data, indent=2)[:3000])
