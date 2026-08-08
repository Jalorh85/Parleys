"""
kbo_api_sports.py — Obtiene partidos REALES y logos OFICIALES de la KBO
usando la API-BASEBALL de api-sports.io.

ESPN no cubre KBO (ver sports_api.py), así que este módulo la reemplaza
como fuente real para esa liga.

Docs: https://api-sports.io/documentation/baseball/v1
Auth: header 'x-apisports-key: <tu_api_key>'
Free tier: 100 requests/día — por eso cacheamos agresivamente
           (league_id y logos no cambian en el día).

Setup:
    export API_SPORTS_KEY="tu_api_key_aqui"
"""

import os
import logging
from datetime import date, timedelta
from typing import Dict, List, Optional
from app.ml.kbo_pitcher_stats import fetch_era_for_matchup

import httpx

logger = logging.getLogger(__name__)

API_SPORTS_BASE = "https://v1.baseball.api-sports.io"
API_SPORTS_KEY = os.environ.get("API_SPORTS_KEY", "721b2f330a081784fcd13aa87d87063b")

# La KBO opera con temporada = año calendario (ej. "2026")
def _current_season(target_date: date) -> int:
    return target_date.year

# ---------------------------------------------------------------------
# Mapeo de nombres api-sports -> nombres internos usados en LEAGUE_TEAMS["KBO"]
# (api-sports a veces devuelve el nombre completo con "KIA Tigers" etc.,
#  pero por robustez mapeamos variantes conocidas)
# ---------------------------------------------------------------------
KBO_TEAM_NAME_MAP: Dict[str, str] = {
    "SSG Landers": "SSG Landers",
    "LG Twins": "LG Twins",
    "KT Wiz": "KT Wiz",
    "kt Wiz": "KT Wiz",
    "NC Dinos": "NC Dinos",
    "Doosan Bears": "Doosan Bears",
    "KIA Tigers": "KIA Tigers",
    "Kia Tigers": "KIA Tigers",
    "Lotte Giants": "Lotte Giants",
    "Samsung Lions": "Samsung Lions",
    "Hanwha Eagles": "Hanwha Eagles",
    "Kiwoom Heroes": "Kiwoom Heroes",
}


def normalize_kbo_team(name: str) -> str:
    return KBO_TEAM_NAME_MAP.get(name, name)


# ---------------------------------------------------------------------
# Caches en memoria (evitan quemar cuota diaria del free tier)
# ---------------------------------------------------------------------
_league_id_cache: Optional[int] = None
_logo_cache: Dict[str, str] = {}  # nombre normalizado -> url del logo oficial


def _headers() -> Dict[str, str]:
    return {"x-apisports-key": API_SPORTS_KEY}


def _get_kbo_league_id() -> Optional[int]:
    """
    Resuelve dinámicamente el ID de la liga KBO en api-sports.
    Se cachea en memoria porque el ID es estable entre temporadas.
    """
    global _league_id_cache
    if _league_id_cache is not None:
        return _league_id_cache

    if not API_SPORTS_KEY:
        logger.warning("API_SPORTS_KEY no configurada — no se puede consultar api-sports")
        return None

    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(
                f"{API_SPORTS_BASE}/leagues",
                headers=_headers(),
                params={"search": "KBO"},
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.TimeoutException:
        logger.error("Timeout al resolver league_id de KBO en api-sports")
        return None
    except httpx.HTTPError as e:
        logger.error(f"Error HTTP resolviendo league_id KBO: {e}")
        return None
    except Exception as e:
        logger.error(f"Error inesperado resolviendo league_id KBO: {e}")
        return None

    results = data.get("response") or []
    if not results:
        # Fallback: algunas cuentas devuelven el nombre completo en vez de "KBO"
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(
                    f"{API_SPORTS_BASE}/leagues",
                    headers=_headers(),
                    params={"country": "South Korea"},
                )
                resp.raise_for_status()
                data = resp.json()
                results = data.get("response") or []
        except Exception as e:
            logger.error(f"Error en fallback de búsqueda de liga KBO: {e}")
            results = []

    if not results:
        logger.error("api-sports no devolvió ninguna liga para KBO")
        return None

   # Tomamos la primera coincidencia; si hay varias, preferimos la que
    # tenga "KBO" en el nombre explícitamente.
    # NOTA: la API de baseball de api-sports devuelve "id"/"name" PLANOS
    # en cada item de "response" (no anidados bajo "league", a diferencia
    # de la API de fútbol de api-sports).
    league = next(
        (r for r in results if "KBO" in (r.get("name", "") or "").upper()),
        results[0],
    )
    league_id = league.get("id")
    if league_id is None:
        logger.error("No se pudo extraer league_id de la respuesta de api-sports")
        return None

    _league_id_cache = int(league_id)
    logger.info(f"KBO league_id resuelto en api-sports: {_league_id_cache}")
    return _league_id_cache


def _get_kbo_team_logos(league_id: int, season: int) -> Dict[str, str]:
    """
    Trae el listado de equipos de la KBO con su logo OFICIAL y lo cachea.
    """
    global _logo_cache
    if _logo_cache:
        return _logo_cache

    if not API_SPORTS_KEY:
        return {}

    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(
                f"{API_SPORTS_BASE}/teams",
                headers=_headers(),
                params={"league": league_id, "season": season},
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.TimeoutException:
        logger.error("Timeout al traer logos de equipos KBO")
        return {}
    except httpx.HTTPError as e:
        logger.error(f"Error HTTP trayendo logos KBO: {e}")
        return {}
    except Exception as e:
        logger.error(f"Error inesperado trayendo logos KBO: {e}")
        return {}

    for item in data.get("response") or []:
        team = item.get("team", {})
        name = normalize_kbo_team(team.get("name", ""))
        logo = team.get("logo", "")
        if name and logo:
            _logo_cache[name] = logo

    logger.info(f"Logos oficiales KBO cacheados: {len(_logo_cache)} equipos")
    return _logo_cache


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


def fetch_kbo_fixtures(target_date: date) -> List[Dict]:
    """
    Punto de entrada principal: partidos reales de KBO + logos oficiales,
    vía api-sports.io. Retorna [] si falta la key, hay error, o no hay
    partidos ese día (mismo comportamiento que get_real_fixtures de ESPN,
    para que el fallback simulado en data_generator.py siga funcionando).
    """
    if not API_SPORTS_KEY:
        logger.info("API_SPORTS_KEY no configurada — KBO usará fallback simulado")
        return []

    league_id = _get_kbo_league_id()
    if league_id is None:
        return []

    season = _current_season(target_date)
    date_str = target_date.strftime("%Y-%m-%d")

    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(
                f"{API_SPORTS_BASE}/games",
                headers=_headers(),
                params={"league": league_id, "season": season, "date": date_str},
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.TimeoutException:
        logger.error(f"Timeout al consultar partidos KBO ({date_str})")
        return []
    except httpx.HTTPError as e:
        logger.error(f"Error HTTP api-sports KBO: {e}")
        return []
    except Exception as e:
        logger.error(f"Error inesperado api-sports KBO: {e}")
        return []

    games = data.get("response") or []
    if not games:
        logger.info(f"api-sports: sin partidos de KBO para el {date_str}")
        return []

    logos = _get_kbo_team_logos(league_id, season)

    fixtures = []
    for idx, game in enumerate(games):
        parsed = _parse_api_sports_game(game, date_str, idx, logos)
        if parsed:
            fixtures.append(parsed)

    logger.info(f"api-sports devolvió {len(fixtures)} partidos de KBO para el {date_str}")
    return fixtures


def get_real_kbo_fixtures(target_date: Optional[date] = None) -> List[Dict]:
    """Alias con la misma firma que get_real_fixtures() de sports_api.py."""
    if target_date is None:
        target_date = date.today() + timedelta(days=1)
    return fetch_kbo_fixtures(target_date)
