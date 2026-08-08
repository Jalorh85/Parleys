"""Test final: verifica que el sistema completo devuelve datos reales"""
import sys
sys.path.insert(0, '.')

from app.ml.sports_api import get_real_fixtures
from app.ml.data_generator import get_upcoming_fixtures
from datetime import date, timedelta

hoy   = date.today()
manana = hoy + timedelta(days=1)

for liga in ["NBA", "MLB", "WNBA", "KBO"]:
    print(f"\n{'='*50}")
    print(f"  {liga}")
    print(f"{'='*50}")
    fixtures = get_upcoming_fixtures(liga, hoy)
    print(f"HOY ({hoy}): {len(fixtures)} partidos — fuente: {fixtures[0]['source'] if fixtures else 'n/a'}")
    for f in fixtures[:3]:
        print(f"  {f['home_team']} vs {f['away_team']} @ {f.get('time','TBD')}")

    fixtures2 = get_upcoming_fixtures(liga, manana)
    print(f"MAÑANA ({manana}): {len(fixtures2)} partidos — fuente: {fixtures2[0]['source'] if fixtures2 else 'n/a'}")
    for f in fixtures2[:3]:
        print(f"  {f['home_team']} vs {f['away_team']} @ {f.get('time','TBD')}")
