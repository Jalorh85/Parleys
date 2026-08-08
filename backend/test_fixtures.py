from app.ml.sports_api import get_real_fixtures
from app.ml.data_generator import get_upcoming_fixtures
import datetime

print("OK: imports correctos")

manana = datetime.date.today() + datetime.timedelta(days=1)
r = get_upcoming_fixtures('NBA', manana)
print(f"Partidos para manana NBA: {len(r)}")
if r:
    print(f"Fuente: {r[0]['source']}")
    print(f"Equipo local: {r[0]['home_team']}")
    print(f"Equipo visitante: {r[0]['away_team']}")
    print(f"Fecha: {r[0]['date']}")
    print(f"Hora: {r[0].get('time', 'N/A')}")
