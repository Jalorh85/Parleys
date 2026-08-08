"""
Corré esto para confirmar que kbo_thesportsdb.py trae partidos y logos
reales antes de dar la integración por hecho.

    uv run python app\\ml\\test_kbo_thesportsdb.py
"""
from datetime import date, timedelta
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from kbo_thesportsdb import fetch_kbo_fixtures, _get_kbo_team_logos

print("=== Logos de equipos KBO (TheSportsDB) ===")
logos = _get_kbo_team_logos()
if not logos:
    print("⚠️  No se encontraron logos. Revisá KBO_LEAGUE_NAME en kbo_thesportsdb.py")
else:
    for team, url in logos.items():
        print(f"  {team}: {url}")

print("\n=== Partidos KBO próximos 10 días ===")
found_any = False
for i in range(10):
    d = date.today() + timedelta(days=i)
    fixtures = fetch_kbo_fixtures(d)
    if fixtures:
        found_any = True
        print(f"\n{d} -> {len(fixtures)} partidos:")
        for f in fixtures:
            print(f"  {f['home_team']} vs {f['away_team']} ({f['time']}) logos: home={bool(f['home_logo'])} away={bool(f['away_logo'])}")

if not found_any:
    print("⚠️  Sin partidos en los próximos 10 días. Puede ser receso de temporada,"
          " o el league_id/nombre está mal. Revisá manualmente en el navegador:")
    print("   https://www.thesportsdb.com/api/v1/json/123/eventsday.php?d=2026-08-08&l=4830")
