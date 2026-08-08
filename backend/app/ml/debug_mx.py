import httpx
import json
from datetime import date, timedelta

print("=== [1] ESPN Liga MX (mex.1) - próximos 10 días ===\n")
found_any = False
with httpx.Client(timeout=10.0, verify=False) as client:
    for i in range(10):
        d = date.today() + timedelta(days=i)
        espn_date = d.strftime("%Y%m%d")
        resp = client.get(
            "https://site.api.espn.com/apis/site/v2/sports/soccer/mex.1/scoreboard",
            params={"dates": espn_date},
        )
        data = resp.json()
        events = data.get("events") or []
        if events:
            found_any = True
            print(f"{d} -> {len(events)} partidos:")
            for ev in events:
                comp = ev.get("competitions", [{}])[0]
                competitors = comp.get("competitors", [])
                home = next((c for c in competitors if c.get("homeAway") == "home"), {})
                away = next((c for c in competitors if c.get("homeAway") == "away"), {})
                home_name = home.get("team", {}).get("displayName", "?")
                away_name = away.get("team", {}).get("displayName", "?")
                home_logo = home.get("team", {}).get("logo", "")
                away_logo = away.get("team", {}).get("logo", "")
                print(f"  {home_name} vs {away_name} | logos: home={bool(home_logo)} away={bool(away_logo)}")

if not found_any:
    print("⚠️  Sin partidos en los próximos 10 días (puede ser receso entre Apertura/Clausura).")

print("\n=== [2] Nombres EXACTOS de equipo que devuelve ESPN (para armar el mapeo) ===\n")
with httpx.Client(timeout=10.0, verify=False) as client:
    resp = client.get("https://site.api.espn.com/apis/site/v2/sports/soccer/mex.1/teams")
    data = resp.json()
    teams_list = data.get("sports", [{}])[0].get("leagues", [{}])[0].get("teams", [])
    for t in teams_list:
        team = t.get("team", {})
        print(f"  '{team.get('displayName')}'")

print("\n=== [3] Logo oficial de Liga MX (TheSportsDB, id=4350) ===\n")
with httpx.Client(timeout=10.0) as client:
    resp = client.get("https://www.thesportsdb.com/api/v1/json/123/lookupleague.php", params={"id": "4350"})
    data = resp.json()
    leagues = data.get("leagues") or []
    if leagues:
        lg = leagues[0]
        print(f"strLeague: {lg.get('strLeague')}")
        print(f"strBadge: {lg.get('strBadge')}")
    else:
        print("Sin respuesta:", json.dumps(data)[:300])
