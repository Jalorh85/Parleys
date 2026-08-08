# Integración de kbo_pitcher_stats.py en kbo_api_sports.py

## Cambio en `_parse_api_sports_game`

Agrega el import arriba del archivo:

```python
from app.ml.kbo_pitcher_stats import fetch_era_for_matchup
```

Y dentro de `_parse_api_sports_game`, justo antes del `return`, mezcla el ERA real:

```python
def _parse_api_sports_game(game: Dict, date_str: str, idx: int, logos: Dict[str, str]) -> Optional[Dict]:
    try:
        teams = game.get("teams", {})
        home_raw = teams.get("home", {}).get("name", "")
        away_raw = teams.get("away", {}).get("name", "")

        if not home_raw or not away_raw:
            return None

        home_team = normalize_kbo_team(home_raw)
        away_team = normalize_kbo_team(away_raw)

        game_date_iso = game.get("date", "")
        time_str = "TBD"
        if "T" in game_date_iso:
            time_part = game_date_iso.split("T")[1]
            time_str = time_part[:5] + " KST"

        home_logo = teams.get("home", {}).get("logo") or logos.get(home_team, "")
        away_logo = teams.get("away", {}).get("logo") or logos.get(away_team, "")

        # --- NUEVO: ERA real de equipo (temporada), vía kbo_pitcher_stats.py ---
        season = int(date_str[:4])
        era_data = fetch_era_for_matchup(home_team, away_team, season)

        return {
            "fixture_id": str(game.get("id", f"APISPORTS-KBO-{idx}")),
            "date": date_str,
            "time": time_str,
            "league": "KBO",
            "home_team": home_team,
            "away_team": away_team,
            "home_team_raw": home_raw,
            "away_team_raw": away_raw,
            "home_logo": home_logo,
            "away_logo": away_logo,
            "source": "API-SPORTS",
            **era_data,   # home_pitcher_era_real / away_pitcher_era_real / pitcher_era_source
        }
    except Exception as e:
        logger.warning(f"Error parseando partido de api-sports: {e}")
        return None
```

Eso es todo. No hace falta tocar `data_generator.py`: `get_upcoming_fixtures()` ya
lee `fix.get("home_pitcher_era_real")` / `fix.get("away_pitcher_era_real")` de
cada fixture "real" (sea ESPN o api-sports) y se los pasa a
`_enrich_fixture_with_profiles`, que ya setea `pitcher_era_is_real: True` cuando
vienen presentes.

## Variables de entorno (resumen completo)

```bash
export API_SPORTS_KEY="tu_api_key_de_api-sports.io"
export API_SPORTS_ENABLE_ERA="true"   # opcional, default true. Ponlo en "false"
                                        # si quieres ahorrar cuota y quedarte solo
                                        # con fixtures + logos, sin ERA real.
```

## Costo real en cuota (free tier: 100 req/día)

Por proceso corriendo (gracias a los caches en memoria de ambos módulos):

| Llamada                              | Frecuencia                          |
|---------------------------------------|--------------------------------------|
| Resolver `league_id` KBO              | 1 vez (se cachea)                    |
| `/teams` (logos)                      | 1 vez (se cachea)                    |
| `/games` (fixtures del día)           | 1 vez por fecha consultada           |
| `/teams` (resolver team_id por equipo)| 1 vez por equipo distinto (≤10 KBO)  |
| `/teams/statistics` (ERA por equipo)  | 1 vez por equipo distinto (≤10 KBO)  |

Peor caso el primer día: ~1 + 1 + 1 + 10 + 10 = 23 requests, y después
todo sale de cache mientras el proceso siga vivo. Si reinicias el server
seguido, considera persistir estos caches en Redis/disco en vez de
memoria del proceso.

## Si más adelante confirmas soporte de "starting pitcher" por partido

El punto de enganche que no cambia es `fetch_era_for_matchup(home_team,
away_team, season)` en `kbo_pitcher_stats.py` — hoy resuelve ERA de
equipo/temporada; se puede reemplazar su interior por una resolución de
`player_id` + `/players/statistics` sin tocar nada en
`kbo_api_sports.py` ni en `data_generator.py`.
