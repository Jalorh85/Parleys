# Integración de kbo_api_sports.py en sports_api.py

## 1. Variable de entorno
```bash
export API_SPORTS_KEY="tu_api_key_de_api-sports.io"
```
(Si no está seteada, KBO simplemente sigue cayendo al simulado — cero riesgo de romper nada.)

## 2. Cambio en `sports_api.py`

Reemplaza la función `get_real_fixtures` por esta versión, que rutea KBO
a api-sports.io y deja el resto (NBA/MLB/WNBA) exactamente igual con ESPN:

```python
def get_real_fixtures(league: str, target_date: Optional[date] = None) -> List[Dict]:
    """
    Punto de entrada principal. Cada liga usa su mejor fuente real:
      - NBA / MLB / WNBA -> ESPN (gratis, sin key)
      - KBO              -> api-sports.io (requiere API_SPORTS_KEY)
    Si no hay datos reales, retorna [] y data_generator.py cae al fallback simulado.
    """
    if target_date is None:
        target_date = date.today() + timedelta(days=1)

    if league == "KBO":
        from app.ml.kbo_api_sports import get_real_kbo_fixtures
        return get_real_kbo_fixtures(target_date)

    return fetch_espn_fixtures(league, target_date)
```

No necesitas tocar `data_generator.py`, `main.py` ni el frontend:
`_enrich_fixture_with_profiles` ya consume `home_logo` / `away_logo` /
`source` sin importar si vienen de ESPN o de api-sports, y `TeamIcon.jsx`
ya renderiza `logoUrl` cuando existe (ver el bloque `if (logoUrl) {...}`
en `TeamIcon.jsx`). En cuanto `API_SPORTS_KEY` esté seteada, los partidos
de KBO en `DailyFixtures.jsx` van a mostrar automáticamente:
- El badge `🟢 Partido Real (API-SPORTS)` en vez de `🟡 Simulado`.
- Los escudos oficiales de los equipos en vez del emoji/inicial genérico.

## 3. Notas sobre cuota (free tier: 100 req/día)

- `_get_kbo_league_id()` y `_get_kbo_team_logos()` cachean en memoria del
  proceso, así que solo gastan request la primera vez que se llaman tras
  un reinicio del servidor.
- Cada llamada a `/api/fixtures?league=KBO` consume **1 request** contra
  `/games`. Si tu tráfico es alto, considera cachear el resultado de
  `fetch_kbo_fixtures` por fecha (ej. con `functools.lru_cache` o Redis)
  para no quemar la cuota diaria.

## 4. ERA de pitchers KBO (opcional, no incluido)

api-sports.io expone estadísticas de jugadores vía `/players` y
`/players/statistics`, pero requiere el `player_id` del pitcher probable,
que no siempre viene en `/games`. Si más adelante quieres ERA real (como
ya tienes para MLB vía ESPN en `home_pitcher_era_real`), puedo armar ese
segundo módulo — por ahora `kbo_api_sports.py` deja `h_pitcher_era` /
`a_pitcher_era` a cargo del estimador sintético existente en
`_enrich_fixture_with_profiles`, igual que hoy.
