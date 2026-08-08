import httpx
import json

BASE = "https://www.thesportsdb.com/api/v1/json/123"

print("=== [1] Nombre exacto de la liga (lookupleague) ===")
with httpx.Client(timeout=10.0) as client:
    resp = client.get(f"{BASE}/lookupleague.php", params={"id": "4830"})
    data = resp.json()
    leagues = data.get("leagues") or []
    exact_name = None
    if leagues:
        exact_name = leagues[0].get("strLeague")
        print(f"Nombre exacto: '{exact_name}'")
        print(f"strLeagueAlternate: {leagues[0].get('strLeagueAlternate')}")
    else:
        print("No devolvió nada. JSON crudo:", json.dumps(data)[:500])

print("\n=== [2] search_all_teams con el nombre EXACTO ===")
if exact_name:
    with httpx.Client(timeout=10.0) as client:
        resp = client.get(f"{BASE}/search_all_teams.php", params={"l": exact_name})
        data = resp.json()
        teams = data.get("teams") or []
        print(f"Equipos encontrados: {len(teams)}")
        for t in teams[:3]:
            print(f"  {t.get('strTeam')} -> badge: {t.get('strTeamBadge')}")

print("\n=== [3] Alternativa: lookup_all_teams por league id ===")
with httpx.Client(timeout=10.0) as client:
    resp = client.get(f"{BASE}/lookup_all_teams.php", params={"id": "4830"})
    data = resp.json()
    teams = data.get("teams") or []
    print(f"Equipos encontrados: {len(teams)}")
    for t in teams[:5]:
        print(f"  {t.get('strTeam')} -> badge: {t.get('strTeamBadge')}")
    if not teams:
        print("JSON crudo:", json.dumps(data)[:800])
