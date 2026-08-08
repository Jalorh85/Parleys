"""Diagnóstico: qué devuelve TheSportsDB para cada liga hoy/mañana"""
import httpx
import json
from datetime import date, timedelta

manana = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
hoy = date.today().strftime("%Y-%m-%d")

LIGAS = ["NBA", "MLB", "WNBA", "KBO"]

for liga in LIGAS:
    for fecha in [hoy, manana]:
        url = f"https://www.thesportsdb.com/api/v1/json/3/eventsday.php"
        try:
            r = httpx.get(url, params={"d": fecha, "l": liga}, timeout=10)
            data = r.json()
            events = data.get("events") or []
            print(f"\n[{liga}] {fecha}: {len(events)} partidos")
            for ev in events[:3]:
                print(f"  {ev.get('strHomeTeam')} vs {ev.get('strAwayTeam')} ({ev.get('strLeague')})")
        except Exception as e:
            print(f"\n[{liga}] {fecha}: ERROR - {e}")
