"""
sports_api.py — Obtiene partidos reales de ESPN (gratis, sin key requerida).
Cobertura: MLB ✅  WNBA ✅  MX ✅ (Liga MX, mex.1)  LCUP ✅ (Leagues Cup 2026, concacaf.leagues.cup)
           NFL ✅ (incluye Pretemporada — ESPN devuelve preseason al consultar por fecha)
           KBO ❌ (usa TheSportsDB)

Documentación ESPN API (no oficial):
  https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard

El slug "concacaf.leagues.cup" para la Leagues Cup fue confirmado contra las
URLs reales de ESPN Deportes (posiciones/resultados), que usan ese mismo
slug para la liga en español, ej:
  https://espndeportes.espn.com/futbol/posiciones/_/liga/concacaf.leagues.cup
"""

import httpx
from datetime import date, timedelta
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

# Endpoints ESPN por liga (gratis, sin autenticación)
ESPN_ENDPOINTS = {
    "MLB":  "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard",
    "WNBA": "https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard",
    "MX":   "https://site.api.espn.com/apis/site/v2/sports/soccer/mex.1/scoreboard",
    "LCUP": "https://site.api.espn.com/apis/site/v2/sports/soccer/concacaf.leagues.cup/scoreboard",
    # NFL: el mismo endpoint de scoreboard devuelve Pretemporada (Preseason)
    # cuando se consulta con el parámetro "dates" en las fechas correspondientes
    # -- no hace falta un slug/seasontype especial, ESPN lo resuelve solo.
    "NFL":  "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard",
    # KBO no está en ESPN → usará TheSportsDB (ver kbo_thesportsdb.py)
}

# Mapeo de nombres de equipo ESPN → nombres internos del modelo ML
# Cubre diferencias de nombre, apodos y equipos de expansión
TEAM_NAME_MAP: Dict[str, str] = {
    # MLB
    "Los Angeles Dodgers":      "Los Angeles Dodgers",
    "New York Yankees":         "New York Yankees",
    "Atlanta Braves":           "Atlanta Braves",
    "Houston Astros":           "Houston Astros",
    "Philadelphia Phillies":    "Philadelphia Phillies",
    "Baltimore Orioles":        "Baltimore Orioles",
    "San Diego Padres":         "San Diego Padres",
    "Texas Rangers":            "Texas Rangers",
    "Seattle Mariners":         "Seattle Mariners",
    "Chicago Cubs":             "Chicago Cubs",
    "Boston Red Sox":           "Boston Red Sox",
    "Minnesota Twins":          "Minnesota Twins",
    "Arizona Diamondbacks":     "Arizona Diamondbacks",
    "Tampa Bay Rays":           "Tampa Bay Rays",
    "Cleveland Guardians":      "Cleveland Guardians",
    "Toronto Blue Jays":        "Toronto Blue Jays",
    # Equipos MLB que espn puede devolver con nombre diferente
    "Athletics":                "Oakland Athletics",
    "Oakland Athletics":        "Oakland Athletics",
    "Chicago White Sox":        "Chicago White Sox",
    "Kansas City Royals":       "Kansas City Royals",
    "Los Angeles Angels":       "Los Angeles Angels",
    "Detroit Tigers":           "Detroit Tigers",
    "New York Mets":            "New York Mets",
    "San Francisco Giants":     "San Francisco Giants",
    "Colorado Rockies":         "Colorado Rockies",
    "Miami Marlins":            "Miami Marlins",
    "Milwaukee Brewers":        "Milwaukee Brewers",
    "Pittsburgh Pirates":       "Pittsburgh Pirates",
    "St. Louis Cardinals":      "St. Louis Cardinals",
    "Cincinnati Reds":          "Cincinnati Reds",
    "Washington Nationals":     "Washington Nationals",
    # WNBA
    "Las Vegas Aces":           "Las Vegas Aces",
    "New York Liberty":         "New York Liberty",
    "Connecticut Sun":          "Connecticut Sun",
    "Minnesota Lynx":           "Minnesota Lynx",
    "Seattle Storm":            "Seattle Storm",
    "Dallas Wings":             "Dallas Wings",
    "Phoenix Mercury":          "Phoenix Mercury",
    "Atlanta Dream":            "Atlanta Dream",
    "Chicago Sky":              "Chicago Sky",
    "Indiana Fever":            "Indiana Fever",
    "Washington Mystics":       "Washington Mystics",
    "Los Angeles Sparks":       "Los Angeles Sparks",
    # WNBA equipos de expansión 2026
    "Portland Fire":            "Portland Fire",
    "Toronto Tempo":            "Toronto Tempo",
    "Golden State Valkyries":   "Golden State Valkyries",
    # Liga MX (nombres EXACTOS confirmados vía ESPN /teams para mex.1)
    "América":                  "América",
    "Atlante":                  "Atlante",
    "Atlas":                    "Atlas",
    "Atlético de San Luis":     "Atlético San Luis",
    "Cruz Azul":                "Cruz Azul",
    "FC Juarez":                "FC Juárez",
    "Guadalajara":              "Guadalajara",
    "León":                     "León",
    "Monterrey":                "Monterrey",
    "Necaxa":                   "Necaxa",
    "Pachuca":                  "Pachuca",
    "Puebla":                   "Puebla",
    "Pumas UNAM":                "Pumas UNAM",
    "Querétaro":                "Querétaro",
    "Santos":                   "Santos Laguna",
    "Tigres UANL":              "Tigres UANL",
    "Tijuana":                  "Tijuana",
    "Toluca":                   "Toluca",
    # --- Leagues Cup 2026: clubes MLS / Canadá (nombres ESPN + variantes) ---
    "Atlanta United":           "Atlanta United",
    "Atlanta United FC":        "Atlanta United",
    "Austin FC":                "Austin FC",
    "CF Montreal":              "CF Montréal",
    "CF Montréal":              "CF Montréal",
    "Charlotte FC":             "Charlotte FC",
    "Chicago Fire":             "Chicago Fire",
    "Chicago Fire FC":          "Chicago Fire",
    "Colorado Rapids":          "Colorado Rapids",
    "Columbus Crew":            "Columbus Crew",
    "Columbus Crew SC":         "Columbus Crew",
    "D.C. United":              "D.C. United",
    "DC United":                "D.C. United",
    "FC Cincinnati":            "FC Cincinnati",
    "FC Dallas":                "FC Dallas",
    "Houston Dynamo":           "Houston Dynamo",
    "Houston Dynamo FC":        "Houston Dynamo",
    "Inter Miami":              "Inter Miami CF",
    "Inter Miami CF":           "Inter Miami CF",
    "LA Galaxy":                "LA Galaxy",
    "Los Angeles FC":           "Los Angeles FC",
    "LAFC":                     "Los Angeles FC",
    "Minnesota United":         "Minnesota United",
    "Minnesota United FC":      "Minnesota United",
    "Nashville SC":             "Nashville SC",
    "New England Revolution":   "New England Revolution",
    "New York City FC":         "New York City FC",
    "NYCFC":                    "New York City FC",
    "New York Red Bulls":       "New York Red Bulls",
    "Orlando City":             "Orlando City",
    "Orlando City SC":          "Orlando City",
    "Philadelphia Union":       "Philadelphia Union",
    "Portland Timbers":         "Portland Timbers",
    "Real Salt Lake":           "Real Salt Lake",
    "San Diego FC":             "San Diego FC",
    "San Jose Earthquakes":     "San Jose Earthquakes",
    "Seattle Sounders":         "Seattle Sounders FC",
    "Seattle Sounders FC":      "Seattle Sounders FC",
    "Sporting Kansas City":     "Sporting Kansas City",
    "Sporting KC":              "Sporting Kansas City",
    "St. Louis City SC":        "St. Louis City SC",
    "St. Louis City":           "St. Louis City SC",
    "Toronto FC":               "Toronto FC",
    "Vancouver Whitecaps":      "Vancouver Whitecaps",
    "Vancouver Whitecaps FC":   "Vancouver Whitecaps",

    # --- NFL (32 equipos) — nombres EXACTOS confirmados vía ESPN /teams
    # para football/nfl y coinciden con los que usa TheSportsDB (liga 4391) ---
    "Arizona Cardinals":        "Arizona Cardinals",
    "Atlanta Falcons":          "Atlanta Falcons",
    "Baltimore Ravens":         "Baltimore Ravens",
    "Buffalo Bills":            "Buffalo Bills",
    "Carolina Panthers":        "Carolina Panthers",
    "Chicago Bears":            "Chicago Bears",
    "Cincinnati Bengals":       "Cincinnati Bengals",
    "Cleveland Browns":         "Cleveland Browns",
    "Dallas Cowboys":           "Dallas Cowboys",
    "Denver Broncos":           "Denver Broncos",
    "Detroit Lions":            "Detroit Lions",
    "Green Bay Packers":        "Green Bay Packers",
    "Houston Texans":           "Houston Texans",
    "Indianapolis Colts":       "Indianapolis Colts",
    "Jacksonville Jaguars":     "Jacksonville Jaguars",
    "Kansas City Chiefs":       "Kansas City Chiefs",
    "Las Vegas Raiders":        "Las Vegas Raiders",
    "Los Angeles Chargers":     "Los Angeles Chargers",
    "Los Angeles Rams":         "Los Angeles Rams",
    "Miami Dolphins":           "Miami Dolphins",
    "Minnesota Vikings":        "Minnesota Vikings",
    "New England Patriots":     "New England Patriots",
    "New Orleans Saints":       "New Orleans Saints",
    "New York Giants":          "New York Giants",
    "New York Jets":            "New York Jets",
    "Philadelphia Eagles":      "Philadelphia Eagles",
    "Pittsburgh Steelers":      "Pittsburgh Steelers",
    "San Francisco 49ers":      "San Francisco 49ers",
    "Seattle Seahawks":         "Seattle Seahawks",
    "Tampa Bay Buccaneers":     "Tampa Bay Buccaneers",
    "Tennessee Titans":         "Tennessee Titans",
    "Washington Commanders":    "Washington Commanders",
}

# También agregar equipos nuevos a la lista de equipos del modelo para WNBA
WNBA_EXPANSION_TEAMS = ["Portland Fire", "Toronto Tempo", "Golden State Valkyries"]


def normalize_team(name: str) -> str:
    """Mapea nombre ESPN al nombre que conoce el modelo ML."""
    return TEAM_NAME_MAP.get(name, name)

def _extract_probable_pitcher(comp: Dict) -> Dict[str, Optional[object]]:
    """
    Extrae nombre y ERA de temporada del pitcher probable de un competidor
    ESPN (home_comp o away_comp), si ya fue publicado.

    Devuelve {"name": str|None, "era": float|None}
    """
    probables = comp.get("probables") or []
    if not probables:
        return {"name": None, "era": None}

    prob = probables[0]
    athlete = prob.get("athlete", {})
    name = athlete.get("displayName") or athlete.get("shortName")

    era = None
    for stat in prob.get("statistics", []):
        stat_name = (stat.get("name") or stat.get("abbreviation") or "").upper()
        if stat_name == "ERA":
            try:
                era = float(stat.get("displayValue"))
            except (TypeError, ValueError):
                era = None
            break

    return {"name": name, "era": era}

def _parse_espn_event(ev: Dict, date_str: str, league: str, idx: int) -> Optional[Dict]:
    """
    Convierte un evento de la API ESPN al formato interno del sistema.
    Ahora también incluye ERA real del pitcher probable para MLB, cuando
    ESPN ya lo publicó.
    """
    try:
        competitions = ev.get("competitions", [{}])[0]
        competitors = competitions.get("competitors", [])

        home_comp = next((c for c in competitors if c.get("homeAway") == "home"), None)
        away_comp = next((c for c in competitors if c.get("homeAway") == "away"), None)

        if not home_comp or not away_comp:
            return None

        home_raw = home_comp.get("team", {}).get("displayName", "")
        away_raw = away_comp.get("team", {}).get("displayName", "")

        if not home_raw or not away_raw:
            return None

        raw_date = ev.get("date", "")
        if "T" in raw_date:
            time_utc = raw_date.split("T")[1].replace("Z", "")
            hour, minute = time_utc.split(":")[:2]
            time_str = f"{hour}:{minute} UTC"
        else:
            time_str = "TBD"

        home_logo = home_comp.get("team", {}).get("logo", "")
        away_logo = away_comp.get("team", {}).get("logo", "")

        result = {
            "fixture_id":    str(ev.get("id", f"ESPN-{league}-{idx}")),
            "date":          date_str,
            "time":          time_str,
            "league":        league,
            "home_team":     normalize_team(home_raw),
            "away_team":     normalize_team(away_raw),
            "home_team_raw": home_raw,
            "away_team_raw": away_raw,
            "home_logo":     home_logo,
            "away_logo":     away_logo,
            "source":        "ESPN",
        }

        # ERA real del pitcher probable — solo aplica a MLB
        if league == "MLB":
            home_pitcher = _extract_probable_pitcher(home_comp)
            away_pitcher = _extract_probable_pitcher(away_comp)
            result["home_pitcher_name"] = home_pitcher["name"]
            result["home_pitcher_era_real"] = home_pitcher["era"]
            result["away_pitcher_name"] = away_pitcher["name"]
            result["away_pitcher_era_real"] = away_pitcher["era"]

        return result
    except Exception as e:
        logger.warning(f"Error parseando evento ESPN: {e}")
        return None



def fetch_espn_fixtures(league: str, target_date: date) -> List[Dict]:
    """
    Consulta ESPN y devuelve partidos para la liga y fecha dadas.
    Retorna lista vacía si la liga no está en ESPN o hay error.
    """
    url = ESPN_ENDPOINTS.get(league)
    if not url:
        logger.info(f"{league} no tiene endpoint ESPN configurado — usará fallback simulado")
        return []

    date_str   = target_date.strftime("%Y-%m-%d")
    espn_date  = target_date.strftime("%Y%m%d")   # ESPN usa YYYYMMDD sin guiones

    try:
        with httpx.Client(timeout=10.0, verify=False) as client:
            resp = client.get(url, params={"dates": espn_date})
            resp.raise_for_status()
            data = resp.json()
    except httpx.TimeoutException:
        logger.error(f"Timeout al consultar ESPN para {league} {date_str}")
        return []
    except httpx.HTTPError as e:
        logger.error(f"Error HTTP ESPN {league}: {e}")
        return []
    except Exception as e:
        logger.error(f"Error inesperado ESPN {league}: {e}")
        return []

    events = data.get("events") or []
    if not events:
        logger.info(f"ESPN: sin partidos para {league} el {date_str} (liga fuera de temporada / sin fecha programada)")
        return []

    fixtures = []
    for idx, ev in enumerate(events):
        parsed = _parse_espn_event(ev, date_str, league, idx)
        if parsed:
            fixtures.append(parsed)

    logger.info(f"ESPN devolvió {len(fixtures)} partidos para {league} el {date_str}")
    return fixtures


def get_real_fixtures(league: str, target_date: Optional[date] = None) -> List[Dict]:
    """
    Punto de entrada principal. Cada liga usa su mejor fuente real:
      - MLB / WNBA / MX / LCUP / NFL -> ESPN (gratis, sin key; NFL incluye Pretemporada)
      - KBO                          -> TheSportsDB v1 (gratis, temporada 2026 activa)
    Si no hay datos reales, retorna [] y data_generator.py cae al fallback simulado.
    """
    if target_date is None:
        target_date = date.today() + timedelta(days=1)

    if league == "KBO":
        from app.ml.kbo_thesportsdb import get_real_kbo_fixtures
        return get_real_kbo_fixtures(target_date)

    return fetch_espn_fixtures(league, target_date)
