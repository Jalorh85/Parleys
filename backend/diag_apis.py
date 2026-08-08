"""Diagnóstico: prueba ESPN API que es gratis y sin key"""
import httpx
from datetime import date, timedelta

hoy = date.today()
manana = hoy + timedelta(days=1)

ESPN_ENDPOINTS = {
    "NBA":  "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard",
    "MLB":  "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard",
    "WNBA": "https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard",
    "KBO":  "https://site.api.espn.com/apis/site/v2/sports/baseball/kbo/scoreboard",
}

for liga, url in ESPN_ENDPOINTS.items():
    for target_date in [hoy, manana]:
        date_str = target_date.strftime("%Y%m%d")  # ESPN usa YYYYMMDD sin guiones
        try:
            r = httpx.get(url, params={"dates": date_str}, timeout=10)
            data = r.json()
            events = data.get("events", [])
            print(f"\n[{liga}] {target_date} -> {len(events)} partidos (ESPN)")
            for ev in events[:3]:
                comps = ev.get("competitions", [{}])[0]
                competitors = comps.get("competitors", [])
                home = next((c for c in competitors if c.get("homeAway") == "home"), {})
                away = next((c for c in competitors if c.get("homeAway") == "away"), {})
                ht = home.get("team", {}).get("displayName", "?")
                at = away.get("team", {}).get("displayName", "?")
                print(f"  {ht} vs {at}")
        except Exception as e:
            print(f"[{liga}] {target_date} ERROR: {e}")

# También probar TheSportsDB con key=1 y nombres alternativos
print("\n\n--- TheSportsDB con diferentes parámetros ---")
tsdb_tests = [
    {"d": str(hoy), "s": "Baseball"},
    {"d": str(hoy), "s": "Basketball"},
    {"d": str(hoy), "l": "NBA"},
    {"d": str(hoy), "l": "Major League Baseball"},
]
for params in tsdb_tests:
    try:
        r = httpx.get("https://www.thesportsdb.com/api/v1/json/1/eventsday.php",
                      params=params, timeout=8)
        data = r.json()
        events = data.get("events") or []
        print(f"Params {params}: {len(events)} partidos")
        if events:
            print(f"  Ejemplo: {events[0].get('strHomeTeam')} vs {events[0].get('strAwayTeam')} ({events[0].get('strLeague')})")
    except Exception as e:
        print(f"Params {params}: ERROR {e}")
