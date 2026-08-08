"""
kbo_thesportsdb.py — Partidos REALES y logos OFICIALES de la KBO usando
TheSportsDB API v1 (gratis).

Por qué este módulo reemplaza a kbo_api_sports.py como fuente primaria:
api-sports.io SÍ tiene la KBO, pero su plan free devuelve este error
para cualquier temporada que no sea 2022-2024:
    "Free plans do not have access to this season, try from 2022 to 2024."
Eso lo vuelve inútil para partidos de temporada actual (2026).

TheSportsDB v1, en cambio, tiene la "Korean KBO League" (id de liga: 4830)
con temporada 2026 activa en su catálogo gratuito, sin tarjeta de crédito.
Se usa la key de prueba pública "123" para arrancar; para producción real
conviene sacar una key propia gratis en https://www.thesportsdb.com/api.php
y configurarla como env var THESPORTSDB_API_KEY.

Docs: https://www.thesportsdb.com/documentation

Endpoints usados (API v1):
  - GET /eventsday.php?d={fecha}&l={league_id}      -> partidos del día
  - GET /search_all_teams.php?l={nombre_liga}        -> TODOS los equipos
        con su logo oficial, en UNA sola llamada (evita 1 request por
        equipo por partido, que quemaría cuota rápido).

Limitación conocida:
TheSportsDB no trae ERA de pitcher probable para KBO -> se deja en None
y data_generator.py cae automáticamente al ERA sintético estimado
(mismo comportamiento que ya tenés para MLB/KBO cuando no hay dato real).
"""

import os
import logging
from datetime import date, timedelta
from typing import Dict, List, Optional

import httpx
import numpy as np

logger = logging.getLogger(__name__)

THESPORTSDB_BASE = "https://www.thesportsdb.com/api/v1/json"
# Key de prueba pública "123" -> funciona sin registro para desarrollo.
# Para producción, sacá tu propia key gratis en thesportsdb.com/api.php
THESPORTSDB_KEY = os.environ.get("THESPORTSDB_API_KEY", "123")

# ID y nombre de liga de "Korean KBO League" en TheSportsDB.
# Confirmado en: https://www.thesportsdb.com/league/4830-korean-kbo-league
KBO_LEAGUE_ID = "4830"
KBO_LEAGUE_NAME = "Korean KBO League"

# ---------------------------------------------------------------------
# Mapeo de nombres TheSportsDB -> nombres internos usados en
# LEAGUE_TEAMS["KBO"] (data_generator.py). TheSportsDB a veces usa
# variantes de nombre distintas a api-sports, así que este mapeo es
# propio y no reutiliza el de kbo_api_sports.py.
# ---------------------------------------------------------------------
KBO_TEAM_NAME_MAP: Dict[str, str] = {
    "SSG Landers": "SSG Landers",
    "LG Twins": "LG Twins",
    "KT Wiz": "KT Wiz",
    "kt wiz": "KT Wiz",
    "KT wiz": "KT Wiz",
    "NC Dinos": "NC Dinos",
    "Doosan Bears": "Doosan Bears",
    "KIA Tigers": "KIA Tigers",
    "Kia Tigers": "KIA Tigers",
    "Lotte Giants": "Lotte Giants",
    "Samsung Lions": "Samsung Lions",
    "Hanwha Eagles": "Hanwha Eagles",
    "Kiwoom Heroes": "Kiwoom Heroes",
    "Nexen Heroes": "Kiwoom Heroes",  # nombre histórico del mismo equipo
}


def normalize_kbo_team(name: str) -> str:
    return KBO_TEAM_NAME_MAP.get(name, name)


# ---------------------------------------------------------------------
# Cache en memoria: nombre normalizado -> URL de logo oficial.
# Se llena con UNA sola llamada a search_all_teams.php, no por partido.
# ---------------------------------------------------------------------
_logo_cache: Dict[str, str] = {}


def _base_url() -> str:
    return f"{THESPORTSDB_BASE}/{THESPORTSDB_KEY}"


def _get_kbo_team_logos() -> Dict[str, str]:
    """
    Trae TODOS los equipos de la KBO con su logo oficial en una sola
    llamada, y los cachea en memoria (los logos no cambian en el día).
    """
    global _logo_cache
    if _logo_cache:
        return _logo_cache

    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(
                f"{_base_url()}/search_all_teams.php",
                params={"l": KBO_LEAGUE_NAME},
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.TimeoutException:
        logger.error("Timeout al traer logos de equipos KBO (TheSportsDB)")
        return {}
    except httpx.HTTPError as e:
        logger.error(f"Error HTTP trayendo logos KBO (TheSportsDB): {e}")
        return {}
    except Exception as e:
        logger.error(f"Error inesperado trayendo logos KBO (TheSportsDB): {e}")
        return {}

    teams = data.get("teams") or []
    for team in teams:
        raw_name = team.get("strTeam", "")
        name = normalize_kbo_team(raw_name)
        # Campos reales de la API (confirmado con /search_all_teams.php):
        # es "strBadge"/"strLogo", NO "strTeamBadge"/"strTeamLogo".
        # strBadge = fondo transparente (mejor para el ícono circular del
        # frontend), strLogo = alternativa si el badge no está disponible.
        logo = team.get("strBadge") or team.get("strLogo") or ""
        if name and logo:
            _logo_cache[name] = logo

    logger.info(f"Logos oficiales KBO cacheados (TheSportsDB): {len(_logo_cache)} equipos")
    return _logo_cache


def _parse_thesportsdb_event(ev: Dict, date_str: str, idx: int, logos: Dict[str, str]) -> Optional[Dict]:
    try:
        home_raw = ev.get("strHomeTeam", "")
        away_raw = ev.get("strAwayTeam", "")

        if not home_raw or not away_raw:
            return None

        home_team = normalize_kbo_team(home_raw)
        away_team = normalize_kbo_team(away_raw)

        time_raw = ev.get("strTime") or ""
        time_str = f"{time_raw[:5]} KST" if time_raw else "TBD"

        home_logo = logos.get(home_team, "")
        away_logo = logos.get(away_team, "")

        return {
            "fixture_id": str(ev.get("idEvent", f"TSDB-KBO-{idx}")),
            "date": date_str,
            "time": time_str,
            "league": "KBO",
            "home_team": home_team,
            "away_team": away_team,
            "home_team_raw": home_raw,
            "away_team_raw": away_raw,
            "home_logo": home_logo,
            "away_logo": away_logo,
            "source": "TheSportsDB",
            # TheSportsDB no trae ERA de pitcher probable para KBO ->
            # queda en None y data_generator.py cae al ERA sintético.
            "home_pitcher_era_real": None,
            "away_pitcher_era_real": None,
        }
    except Exception as e:
        logger.warning(f"Error parseando evento de TheSportsDB: {e}")
        return None


def fetch_kbo_fixtures(target_date: date) -> List[Dict]:
    """
    Punto de entrada principal: partidos reales de KBO + logos oficiales,
    vía TheSportsDB v1. Retorna [] si hay error o no hay partidos ese día
    (mismo contrato que get_real_fixtures de ESPN, para que el fallback
    simulado en data_generator.py siga funcionando).
    """
    date_str = target_date.strftime("%Y-%m-%d")

    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(
                f"{_base_url()}/eventsday.php",
                params={"d": date_str, "l": KBO_LEAGUE_ID},
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.TimeoutException:
        logger.error(f"Timeout al consultar TheSportsDB KBO ({date_str})")
        return []
    except httpx.HTTPError as e:
        logger.error(f"Error HTTP TheSportsDB KBO: {e}")
        return []
    except Exception as e:
        logger.error(f"Error inesperado TheSportsDB KBO: {e}")
        return []

    events = data.get("events") or []
    if not events:
        logger.info(f"TheSportsDB: sin partidos de KBO para el {date_str}")
        return []

    logos = _get_kbo_team_logos()

    fixtures = []
    for idx, ev in enumerate(events):
        parsed = _parse_thesportsdb_event(ev, date_str, idx, logos)
        if parsed:
            fixtures.append(parsed)

    logger.info(f"TheSportsDB devolvió {len(fixtures)} partidos de KBO para el {date_str}")
    return fixtures


def get_real_kbo_fixtures(target_date: Optional[date] = None) -> List[Dict]:
    """Alias con la misma firma que get_real_fixtures() de sports_api.py."""
    if target_date is None:
        target_date = date.today() + timedelta(days=1)
    return fetch_kbo_fixtures(target_date)


# ---------------------------------------------------------------------
# Perfiles de equipo REALES (standings de temporada) vía TheSportsDB.
#
# Hasta ahora KBO era la única liga cuyos perfiles de equipo (off_rating,
# def_rating, home_adv) salían 100% de np.random (generate_team_profiles en
# data_generator.py) -- MLB/WNBA/MX/LCUP sí tienen su versión real basada en
# resultados de ESPN (espn_historical.py), pero KBO no está en ESPN. Esto
# usa la tabla de posiciones real de TheSportsDB (carreras a favor/en contra,
# victorias) para calcular perfiles reales, en la MISMA escala (~100±10) que
# usa el resto del pipeline, así estimate_matchup_bias() los combina sin
# necesitar ningún caso especial.
# ---------------------------------------------------------------------

_standings_cache: Dict[str, List[Dict]] = {}


def _get_kbo_standings(season: Optional[str] = None) -> List[Dict]:
    if season is None:
        season = str(date.today().year)
    if season in _standings_cache:
        return _standings_cache[season]

    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(
                f"{_base_url()}/lookuptable.php",
                params={"l": KBO_LEAGUE_ID, "s": season},
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.TimeoutException:
        logger.error(f"Timeout al traer standings KBO (TheSportsDB, temporada {season})")
        return []
    except httpx.HTTPError as e:
        logger.error(f"Error HTTP trayendo standings KBO (TheSportsDB): {e}")
        return []
    except Exception as e:
        logger.error(f"Error inesperado trayendo standings KBO (TheSportsDB): {e}")
        return []

    table = data.get("table") or []
    if table:
        _standings_cache[season] = table
    return table


def get_real_kbo_team_profiles(season: Optional[str] = None) -> Dict[str, Dict]:
    """
    Perfiles de equipo KBO calculados a partir de la tabla de posiciones REAL
    de la temporada (carreras a favor/en contra por partido, % de victorias),
    en vez del rating sintético. Retorna {} si TheSportsDB no tiene la tabla
    disponible o si hay muy pocos equipos con datos válidos -- en ese caso
    el llamador debe caer al fallback sintético (mismo contrato que
    fetch_kbo_fixtures / get_real_fixtures).
    """
    table = _get_kbo_standings(season)
    if not table:
        return {}

    parsed_rows = []
    for row in table:
        raw_name = row.get("strTeam", "")
        name = normalize_kbo_team(raw_name)
        try:
            played = int(row.get("intPlayed") or 0)
            wins = int(row.get("intWin") or 0)
            runs_for = float(row.get("intGoalsFor") or 0)
            runs_against = float(row.get("intGoalsAgainst") or 0)
        except (TypeError, ValueError):
            continue
        if not name or played <= 0:
            continue
        parsed_rows.append({
            "name": name,
            "rf_pg": runs_for / played,
            "ra_pg": runs_against / played,
            "win_pct": wins / played,
        })

    # Muy pocos equipos con datos válidos -> no es confiable, que el llamador
    # use el fallback sintético en su lugar.
    if len(parsed_rows) < 4:
        logger.warning(f"Standings KBO insuficientes en TheSportsDB ({len(parsed_rows)} equipos) — usando fallback sintético")
        return {}

    league_rf = float(np.mean([r["rf_pg"] for r in parsed_rows]))
    league_ra = float(np.mean([r["ra_pg"] for r in parsed_rows]))

    profiles: Dict[str, Dict] = {}
    for r in parsed_rows:
        # Escala: +1 carrera/partido por encima del promedio de liga -> +4pts
        # de rating, para quedar en el mismo rango (~100±10-15) que usa el
        # resto del sistema (generate_team_profiles).
        off_rating = 100.0 + (r["rf_pg"] - league_rf) * 4.0
        # Nota de signo: def_rating "alto" acá significa MÁS carreras
        # permitidas (peor defensa) -- estimate_matchup_bias ya resta
        # (a_def - h_def), así que no hay que invertir el signo acá.
        def_rating = 100.0 + (r["ra_pg"] - league_ra) * 4.0
        home_adv = round(2.0 + r["win_pct"] * 1.5, 2)  # 2.0-3.5, proxy sin splits local/visita
        # TheSportsDB no publica ERA real de pitcher para KBO (ver docstring
        # del módulo) -> se estima a partir de carreras permitidas por partido.
        pitching_era = round(max(2.5, r["ra_pg"] * 1.05), 2)

        profiles[r["name"]] = {
            "off_rating": round(off_rating, 2),
            "def_rating": round(def_rating, 2),
            "home_adv": home_adv,
            "pace": 50.0,
            "pitching_era": pitching_era,
            "source": "TheSportsDB",
        }

    logger.info(f"Perfiles reales de KBO calculados desde TheSportsDB para {len(profiles)} equipos")
    return profiles
