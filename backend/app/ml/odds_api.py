"""
odds_api.py — Cuotas REALES de casas de apuestas, vía The Odds API
(https://the-odds-api.com -- v4). OJO: no confundir con "theoddsapi.com"
(sin guion), que es un servicio distinto de otra empresa, con otra
autenticación (x-api-key) y otro catálogo/precios.

Por qué existe este módulo: antes, sb_home_odds/sb_away_odds/sb_spread/
sb_total se ESTIMABAN dentro de estimate_matchup_bias() a partir de la
misma probabilidad que el ensemble usa para predecir el partido -- es
decir, el detector de "+EV" comparaba el modelo contra una versión de sí
mismo, nunca contra el mercado real, así que nunca podía encontrar valor
real, solo medía consistencia interna. Este módulo trae la cuota real de
sportsbooks de EE.UU. cuando está disponible; el ensemble, los features y
los perfiles de equipo siguen exactamente igual -- lo único que cambia es
CONTRA QUÉ línea se compara el value bet.

Configuración (variables de entorno):
  ODDS_API_KEY         -- tu API key de the-odds-api.com. Si no está
                           seteada, este módulo no hace NINGÚN request --
                           toda la app sigue funcionando con las cuotas
                           estimadas de siempre, sin romper nada.
  ODDS_CACHE_TTL_HOURS  -- horas que se cachea la lista de cuotas de una
                           liga antes de volver a pedirle a la API
                           (default 12).

Presupuesto de créditos (plan gratis = 500 requests/mes, ~16/día):
  Con TTL=12h y las 4 ligas cubiertas (MLB, WNBA, NFL, Liga MX -- LCUP y
  KBO no están en el catálogo de the-odds-api.com), el máximo es
  4 ligas x 2 refrescos/día = 8 requests/día = ~240/mes. Deja margen para
  bajar el TTL si querés líneas más frescas, sin quedarte sin créditos a
  mitad de mes. Un solo request trae TODOS los partidos del día de esa
  liga -- no se pide por partido.
"""

import os
import logging
import threading
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

logger = logging.getLogger("parleys_ai")

ODDS_API_KEY = os.environ.get("ODDS_API_KEY", "").strip()
ODDS_API_BASE = "https://api.the-odds-api.com/v4"
ODDS_CACHE_TTL_HOURS = float(os.environ.get("ODDS_CACHE_TTL_HOURS", "12"))

# Ligas cubiertas por the-odds-api.com. LCUP (Leagues Cup, torneo de verano
# de mitad de temporada) y KBO no están en su catálogo -- para esas dos,
# get_real_odds_events() devuelve [] sin gastar créditos, y cada fixture
# sigue usando la cuota estimada de siempre (ver data_generator.py).
LEAGUE_TO_ODDS_SPORT_KEY: Dict[str, str] = {
    "MLB": "baseball_mlb",
    "WNBA": "basketball_wnba",
    "NFL": "americanfootball_nfl",
    "MX": "soccer_mexico_ligamx",
}

_cache: Dict[str, Dict] = {}  # league -> {"fetched_at": datetime, "events": [...]}
_cache_lock = threading.Lock()


def _fetch_odds_events(league: str) -> List[Dict]:
    sport_key = LEAGUE_TO_ODDS_SPORT_KEY.get(league)
    if not sport_key or not ODDS_API_KEY:
        return []

    import httpx
    url = f"{ODDS_API_BASE}/sports/{sport_key}/odds"
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "us",
        "markets": "h2h,spreads,totals",
        "oddsFormat": "decimal",  # mismo formato que ya usa sb_home_odds/sb_away_odds en la app
    }
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            remaining = resp.headers.get("x-requests-remaining")
            if remaining is not None:
                logger.info(f"the-odds-api ({league}): créditos restantes este mes: {remaining}")
            return resp.json()
    except Exception as e:
        logger.warning(f"No se pudieron obtener cuotas reales para {league}: {e}")
        return []


def get_real_odds_events(league: str) -> List[Dict]:
    """
    Lista de eventos con cuotas reales para la liga (todos los partidos del
    día en un solo request), cacheada ODDS_CACHE_TTL_HOURS horas para no
    gastar créditos de más. Devuelve [] sin hacer ningún request si
    ODDS_API_KEY no está seteada o la liga no está cubierta.
    """
    if league not in LEAGUE_TO_ODDS_SPORT_KEY or not ODDS_API_KEY:
        return []

    with _cache_lock:
        cached = _cache.get(league)
        if cached:
            age = datetime.now(timezone.utc) - cached["fetched_at"]
            if age < timedelta(hours=ODDS_CACHE_TTL_HOURS):
                return cached["events"]

        events = _fetch_odds_events(league)
        if events:
            _cache[league] = {"fetched_at": datetime.now(timezone.utc), "events": events}
            return events
        # Si el fetch falló pero había algo cacheado (aunque vencido), mejor
        # usar eso un rato más que quedarnos sin nada.
        return cached["events"] if cached else []


def _norm(name: str) -> str:
    return (name or "").lower().strip()


def _teams_match(name_a: str, name_b: str) -> bool:
    a, b = _norm(name_a), _norm(name_b)
    if not a or not b:
        return False
    if a == b:
        return True
    # Fallback: coincidencia por la última palabra significativa (mascota) --
    # ej. "LA Dodgers" vs "Los Angeles Dodgers" -> "dodgers" == "dodgers".
    # Cubre pequeñas diferencias de naming entre the-odds-api.com y ESPN.
    return a.split()[-1] == b.split()[-1]


def match_fixture_odds(events: List[Dict], home_team: str, away_team: str) -> Optional[Dict]:
    """
    Busca, dentro de la lista de eventos con cuotas reales de una liga, el
    que corresponde a home_team vs away_team, y devuelve las líneas
    normalizadas al mismo formato que ya usa el resto de la app
    (sb_home_odds/sb_away_odds/sb_spread/sb_total), o None si no hay match
    (partido todavía no listado, liga sin cobertura, etc.). El spread y el
    total son la MEDIANA entre todos los bookmakers que ofrecen esa línea,
    más estable que tomar un solo libro.
    """
    if not events:
        return None

    match = next(
        (ev for ev in events
         if _teams_match(ev.get("home_team", ""), home_team)
         and _teams_match(ev.get("away_team", ""), away_team)),
        None,
    )
    if not match:
        return None

    home_prices, away_prices, spread_points, total_points = [], [], [], []
    for bk in match.get("bookmakers", []):
        for market in bk.get("markets", []):
            key = market.get("key")
            outcomes = market.get("outcomes", [])
            if key == "h2h":
                for outcome in outcomes:
                    if _teams_match(outcome.get("name", ""), home_team):
                        home_prices.append(outcome["price"])
                    elif _teams_match(outcome.get("name", ""), away_team):
                        away_prices.append(outcome["price"])
            elif key == "spreads":
                for outcome in outcomes:
                    if _teams_match(outcome.get("name", ""), home_team) and outcome.get("point") is not None:
                        spread_points.append(outcome["point"])
            elif key == "totals":
                for outcome in outcomes:
                    if outcome.get("name") == "Over" and outcome.get("point") is not None:
                        total_points.append(outcome["point"])

    if not home_prices or not away_prices:
        return None  # sin moneyline no hay mucho que usar

    def _median(vals: List[float]) -> float:
        s = sorted(vals)
        n = len(s)
        return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2.0

    result: Dict = {
        "sb_home_odds": round(_median(home_prices), 2),
        "sb_away_odds": round(_median(away_prices), 2),
    }
    if spread_points:
        result["sb_spread"] = round(_median(spread_points), 1)
    if total_points:
        result["sb_total"] = round(_median(total_points), 1)

    return result
