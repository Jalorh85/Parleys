"""
kbo_pitcher_stats.py — ERA real de los equipos de la KBO, vía la API-BASEBALL
de api-sports.io (endpoint /teams/statistics).

IMPORTANTE — limitación conocida:
api-sports.io no documenta públicamente un endpoint de "pitcher probable"
por partido para KBO (a diferencia de ESPN, que sí lo da para MLB). Por
eso este módulo NO intenta adivinar quién abre el juego; en su lugar trae
el ERA REAL agregado del staff de pitcheo de cada equipo en la temporada
(/teams/statistics). Es un dato real (no simulado), pero a nivel de
equipo, no del pitcher individual que abre ese día puntual.

Si tu plan de api-sports confirma soporte de "starting pitcher" a nivel
de partido, este módulo se puede refinar para resolver el player_id y
consultar /players/statistics en su lugar — el punto de enganche
(fetch_era_for_matchup) queda igual, solo cambiaría la implementación
interna.

Setup: reutiliza la misma API_SPORTS_KEY que kbo_api_sports.py.
"""

import os
import logging
from typing import Dict, Optional, Tuple, Any

import httpx

from app.ml.kbo_api_sports import (
    API_SPORTS_BASE,
    API_SPORTS_KEY,
    normalize_kbo_team,
    _get_kbo_league_id,
)

logger = logging.getLogger(__name__)

# Activar/desactivar explícitamente por env var: cada equipo nuevo consulta
# 2 endpoints (team id + team stats) la primera vez. Con 10 equipos en la
# KBO son ~20 requests una sola vez por día de proceso corriendo — cabe
# holgado en el free tier (100/día), pero lo dejamos opt-in por si ya
# estás usando la cuota para otra cosa.
ENABLE_TEAM_ERA_LOOKUP = os.environ.get("API_SPORTS_ENABLE_ERA", "true").lower() == "true"

# ---------------------------------------------------------------------
# Caches en memoria (por proceso) — evitan quemar cuota diaria
# ---------------------------------------------------------------------
_team_id_cache: Dict[str, int] = {}       # nombre normalizado -> team_id
_team_era_cache: Dict[Tuple[str, int], float] = {}  # (nombre, season) -> ERA


def _headers() -> Dict[str, str]:
    return {"x-apisports-key": API_SPORTS_KEY}


def _get_kbo_team_id(team_name: str, league_id: int, season: int) -> Optional[int]:
    """Resuelve el team_id de api-sports para un equipo de la KBO, cacheado."""
    norm = normalize_kbo_team(team_name)
    if norm in _team_id_cache:
        return _team_id_cache[norm]

    if not API_SPORTS_KEY:
        return None

    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(
                f"{API_SPORTS_BASE}/teams",
                headers=_headers(),
                params={"league": league_id, "season": season, "search": norm},
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.TimeoutException:
        logger.error(f"Timeout resolviendo team_id de {norm}")
        return None
    except httpx.HTTPError as e:
        logger.error(f"Error HTTP resolviendo team_id de {norm}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error inesperado resolviendo team_id de {norm}: {e}")
        return None

    results = data.get("response") or []
    if not results:
        logger.warning(f"api-sports no encontró team_id para '{norm}' (KBO)")
        return None

    team_id = results[0].get("team", {}).get("id")
    if team_id is None:
        return None

    _team_id_cache[norm] = int(team_id)
    return _team_id_cache[norm]


def _find_era_recursive(obj: Any) -> Optional[float]:
    """
    Busca de forma defensiva un valor de ERA dentro de la respuesta de
    /teams/statistics, sin asumir una ruta de claves fija (el esquema
    exacto de api-sports para esta liga no está 100% confirmado en su
    documentación pública). Busca cualquier clave que contenga 'era'
    (case-insensitive) cuyo valor sea numérico o un string numérico.
    """
    if isinstance(obj, dict):
        for key, value in obj.items():
            if "era" in key.lower() and not isinstance(value, (dict, list)):
                try:
                    return float(value)
                except (TypeError, ValueError):
                    continue
        for value in obj.values():
            found = _find_era_recursive(value)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = _find_era_recursive(item)
            if found is not None:
                return found
    return None


def get_team_era(team_name: str, season: int) -> Optional[float]:
    """
    ERA real del staff de pitcheo del equipo en la temporada dada.
    Retorna None si no se puede resolver (sin key, error de red, equipo
    no encontrado, o el esquema de respuesta no trae ERA reconocible).
    """
    if not ENABLE_TEAM_ERA_LOOKUP or not API_SPORTS_KEY:
        return None

    norm = normalize_kbo_team(team_name)
    cache_key = (norm, season)
    if cache_key in _team_era_cache:
        return _team_era_cache[cache_key]

    league_id = _get_kbo_league_id()
    if league_id is None:
        return None

    team_id = _get_kbo_team_id(norm, league_id, season)
    if team_id is None:
        return None

    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(
                f"{API_SPORTS_BASE}/teams/statistics",
                headers=_headers(),
                params={"team": team_id, "league": league_id, "season": season},
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.TimeoutException:
        logger.error(f"Timeout trayendo estadísticas de {norm}")
        return None
    except httpx.HTTPError as e:
        logger.error(f"Error HTTP trayendo estadísticas de {norm}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error inesperado trayendo estadísticas de {norm}: {e}")
        return None

    era = _find_era_recursive(data.get("response"))
    if era is None:
        logger.info(f"api-sports: no se encontró ERA reconocible para {norm} (season {season})")
        return None

    era = round(era, 2)
    _team_era_cache[cache_key] = era
    return era


def fetch_era_for_matchup(home_team: str, away_team: str, season: int) -> Dict[str, Optional[Any]]:
    """
    Punto de entrada usado por kbo_api_sports.py al armar cada fixture.
    Devuelve un dict listo para mezclar en el fixture:
        {
          "home_pitcher_era_real": float | None,
          "away_pitcher_era_real": float | None,
          "pitcher_era_source": "team_season_avg" | None,
        }
    Si algo falla, todo queda en None y _enrich_fixture_with_profiles en
    data_generator.py cae automáticamente al ERA estimado sintético
    (mismo comportamiento que ya tienes para MLB/ESPN cuando no hay dato).
    """
    home_era = get_team_era(home_team, season)
    away_era = get_team_era(away_team, season)

    if home_era is None or away_era is None:
        return {
            "home_pitcher_era_real": None,
            "away_pitcher_era_real": None,
            "pitcher_era_source": None,
        }

    return {
        "home_pitcher_era_real": home_era,
        "away_pitcher_era_real": away_era,
        "pitcher_era_source": "team_season_avg",
    }
