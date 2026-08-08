import httpx
import json

BASE = "https://www.thesportsdb.com/api/v1/json/123"

with httpx.Client(timeout=10.0) as client:
    resp = client.get(f"{BASE}/search_all_teams.php", params={"l": "Korean KBO League"})
    data = resp.json()
    teams = data.get("teams") or []

print(f"Total equipos: {len(teams)}\n")

if teams:
    print("=== JSON COMPLETO del primer equipo (Doosan Bears) ===")
    print(json.dumps(teams[0], indent=2, ensure_ascii=False))

    print("\n=== Solo campos que contienen 'logo', 'badge', 'thumb', 'jersey', 'crest' o 'image' (case-insensitive) ===")
    for t in teams:
        name = t.get("strTeam")
        img_fields = {k: v for k, v in t.items() if v and any(
            kw in k.lower() for kw in ["logo", "badge", "thumb", "jersey", "crest", "image", "banner"]
        )}
        print(f"{name}: {img_fields}")
