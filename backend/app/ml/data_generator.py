import numpy as np
import pandas as pd
import logging
import hashlib
from datetime import date, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


def _stable_seed(s: str) -> int:
    """
    Semilla determinista a partir de un string, para reemplazar el hash()
    built-in de Python en todo lo que siembra np.random en este archivo.

    hash() de strings en Python está sujeto a PYTHONHASHSEED, que se
    randomiza en cada arranque de proceso (por seguridad, desde Python
    3.3) -- eso significa que el mismo string ("LCUP", "2026-08-15América
    Guadalajara", etc.) produce un hash DISTINTO cada vez que se levanta
    un proceso nuevo (cada deploy, y en serverless a veces cada cold
    start). Como resultado, los perfiles sintéticos de equipos, el
    dataset histórico sintético con el que se re-entrena el modelo, y
    hasta el home_form/away_form/home_rest/away_rest de un fixture
    puntual cambiaban de valor de un despliegue a otro aunque el partido,
    la fecha y el input fueran exactamente los mismos -- eso es lo que
    hacía que la predicción de un mismo partido "cambiara sola".

    hashlib SÍ es determinista entre procesos (no depende de
    PYTHONHASHSEED), así que el mismo string siempre da la misma semilla.
    """
    return int(hashlib.md5(s.encode("utf-8")).hexdigest(), 16)


# --- Clubes Liga MX (mismos 18 que ya usa la liga "MX") ---
_MX_TEAMS = [
    "América", "Atlante", "Atlas", "Atlético San Luis", "Cruz Azul",
    "FC Juárez", "Guadalajara", "León", "Monterrey", "Necaxa",
    "Pachuca", "Puebla", "Pumas UNAM", "Querétaro", "Santos Laguna",
    "Tigres UANL", "Tijuana", "Toluca"
]

# --- Clubes MLS / Canadá que participan en la Leagues Cup 2026 ---
# Lista confirmada contra el roster real de la Leagues Cup 2026 (TheSportsDB,
# league/5281-leagues-cup) — 30 clubes de EE.UU. y Canadá.
_MLS_TEAMS = [
    "Atlanta United", "Austin FC", "CF Montréal", "Charlotte FC", "Chicago Fire",
    "Colorado Rapids", "Columbus Crew", "D.C. United", "FC Cincinnati", "FC Dallas",
    "Houston Dynamo", "Inter Miami CF", "LA Galaxy", "Los Angeles FC", "Minnesota United",
    "Nashville SC", "New England Revolution", "New York City FC", "New York Red Bulls",
    "Orlando City", "Philadelphia Union", "Portland Timbers", "Real Salt Lake",
    "San Diego FC", "San Jose Earthquakes", "Seattle Sounders FC", "Sporting Kansas City",
    "St. Louis City SC", "Toronto FC", "Vancouver Whitecaps"
]

# --- Los 32 equipos de la NFL (nombres EXACTOS que usa ESPN, ver sports_api.py) ---
_NFL_TEAMS = [
    "Arizona Cardinals", "Atlanta Falcons", "Baltimore Ravens", "Buffalo Bills",
    "Carolina Panthers", "Chicago Bears", "Cincinnati Bengals", "Cleveland Browns",
    "Dallas Cowboys", "Denver Broncos", "Detroit Lions", "Green Bay Packers",
    "Houston Texans", "Indianapolis Colts", "Jacksonville Jaguars", "Kansas City Chiefs",
    "Las Vegas Raiders", "Los Angeles Chargers", "Los Angeles Rams", "Miami Dolphins",
    "Minnesota Vikings", "New England Patriots", "New Orleans Saints", "New York Giants",
    "New York Jets", "Philadelphia Eagles", "Pittsburgh Steelers", "San Francisco 49ers",
    "Seattle Seahawks", "Tampa Bay Buccaneers", "Tennessee Titans", "Washington Commanders"
]

LEAGUE_TEAMS = {
    "LCUP": _MX_TEAMS + _MLS_TEAMS,  # Leagues Cup 2026 — Liga MX vs MLS/Canadá
    "MLB": [
        "Los Angeles Dodgers", "New York Yankees", "Atlanta Braves", "Houston Astros",
        "Philadelphia Phillies", "Baltimore Orioles", "San Diego Padres", "Texas Rangers",
        "Seattle Mariners", "Chicago Cubs", "Boston Red Sox", "Minnesota Twins",
        "Arizona Diamondbacks", "Tampa Bay Rays", "Cleveland Guardians", "Toronto Blue Jays",
        # Equipos MLB adicionales (los 30 equipos)
        "New York Mets", "San Francisco Giants", "Colorado Rockies", "Miami Marlins",
        "Milwaukee Brewers", "Pittsburgh Pirates", "St. Louis Cardinals", "Cincinnati Reds",
        "Washington Nationals", "Detroit Tigers", "Kansas City Royals", "Los Angeles Angels",
        "Chicago White Sox", "Oakland Athletics"
    ],
    "WNBA": [
        "Las Vegas Aces", "New York Liberty", "Connecticut Sun", "Minnesota Lynx",
        "Seattle Storm", "Dallas Wings", "Phoenix Mercury", "Atlanta Dream",
        "Chicago Sky", "Indiana Fever", "Washington Mystics", "Los Angeles Sparks",
        # Equipos de expansión WNBA 2026
        "Portland Fire", "Toronto Tempo", "Golden State Valkyries"
    ],
    "KBO": [
        "SSG Landers", "LG Twins", "KT Wiz", "NC Dinos",
        "Doosan Bears", "KIA Tigers", "Lotte Giants", "Samsung Lions",
        "Hanwha Eagles", "Kiwoom Heroes"
    ],
    "MX": _MX_TEAMS,
    "NFL": _NFL_TEAMS
}

LEAGUE_BASE_TOTALS = {
    "LCUP": (2.9, 1.6),     # Goles totales por partido (fútbol, torneo eliminatorio de verano)
    "MLB": (8.5, 2.1),
    "WNBA": (163.5, 9.5),
    "KBO": (9.8, 2.4),
    "MX": (2.6, 1.4),       # Goles totales por partido (fútbol)
    "NFL": (43.5, 13.5)     # Puntos totales por partido (histórico NFL ~43-45; Pretemporada
                             # es algo más volátil por rotación de roster, de ahí el std alto)
}

LEAGUE_BASE_MARGINS = {
    "LCUP": (0.0, 1.7),     # Diferencia de goles
    "MLB": (0.0, 3.2),
    "WNBA": (0.0, 9.8),
    "KBO": (0.0, 3.5),
    "MX": (0.0, 1.6),       # Diferencia de goles
    "NFL": (0.0, 14.0)      # Diferencia de puntos
}

# Media/std de tiros de esquina TOTALES por partido (solo aplica a fútbol -> MX, LCUP)
LEAGUE_BASE_CORNERS = {
    "MX": (10.2, 3.2),
    "LCUP": (10.0, 3.2)
}

# Ligas de fútbol (comparten reglas de redondeo, córners, etc.)
SOCCER_LEAGUES = ["MX", "LCUP"]

# Cota de seguridad sobre el SESGO esperado (antes del ruido aleatorio) para
# ligas de fútbol. No limita el resultado final del partido (que sí puede
# tener partidos de 6-7 goles ocasionalmente, eso es realista) — limita que
# la fórmula misma pueda "irse" a un sesgo absurdo si algún input viene en
# un extremo raro. Ver estimate_matchup_bias() para el porqué de esto.
SOCCER_MARGIN_CLIP = (-5.0, 5.0)   # diferencia de goles esperada
SOCCER_TOTAL_CLIP = (1.0, 5.5)     # goles totales esperados

# Ligas de béisbol (comparten la misma escala de carreras).
BASEBALL_LEAGUES = ["MLB", "KBO"]

# Fútbol americano (NFL). Misma razón que fútbol/béisbol: los ratings están
# normalizados en escala NBA (off_rating/def_rating ~100±10, home_adv 2-5,
# form en [0,1]) y hay que comprimirlos a la escala real de puntos de la NFL
# (~43.5 puntos totales, margen con std ~14) en vez de sumarlos punto por
# punto como en baloncesto -- si no, el sesgo esperado se dispara muy por
# encima de lo que un partido de NFL produce realmente.
FOOTBALL_LEAGUES = ["NFL"]
FOOTBALL_MARGIN_CLIP = (-24.0, 24.0)   # diferencia de puntos esperada
FOOTBALL_TOTAL_CLIP = (28.0, 62.0)     # puntos totales esperados

# Igual que con fútbol: la rama "genérica" de más abajo está calibrada para
# baloncesto (ratings ~100±10, puntajes ~100-225). Aplicada sin ajustar a
# béisbol (carreras ~7-12 por partido) producía hándicaps absurdos (+9/+10
# carreras) y totales de 20+ carreras para KBO/MLB. Estas cotas acotan el
# sesgo esperado a un rango realista de béisbol.
BASEBALL_MARGIN_CLIP = (-6.0, 6.0)   # diferencia de carreras esperada
BASEBALL_TOTAL_CLIP = (4.0, 16.0)    # carreras totales esperadas


def estimate_matchup_bias(league: str, h_prof: Dict, a_prof: Dict,
                           home_form: float = 0.5, away_form: float = 0.5,
                           home_rest: int = 1, away_rest: int = 1) -> Dict[str, float]:
    """
    Calcula el SESGO esperado (margen y total, antes de sumar ruido
    aleatorio) a partir de los ratings de los dos equipos.

    Este es el ÚNICO lugar donde vive esta fórmula. Antes estaba
    triplicada — una copia en generate_historical_dataset() (dataset
    sintético), otra en _enrich_fixture_with_profiles() (fixtures en vivo)
    y otra más en espn_historical.py (dataset real de ESPN) — y las tres
    reutilizaban coeficientes calibrados para baloncesto (off_rating/
    def_rating/home_adv/form están normalizados en escala NBA, con totales
    de ~100-225) aplicados sin ajustar a fútbol (totales de ~2.6-2.9
    goles). Esa es la causa de líneas y totales irreales (+11 goles, etc.)
    en Liga MX y Leagues Cup: la misma variación relativa que en NBA es
    ruido razonable, en fútbol es 10-15x el total real del partido.

    Al centralizar el cálculo acá, cualquier corrección futura se aplica
    una sola vez y los 3 caminos (sintético / en vivo / ESPN real) quedan
    siempre coherentes entre sí.
    """
    mean_tot, _ = LEAGUE_BASE_TOTALS.get(league, (200.0, 10.0))
    off_diff = h_prof["off_rating"] - a_prof["off_rating"]

    if league in SOCCER_LEAGUES:
        # Coeficientes propios de fútbol: la misma señal relativa (off_rating,
        # home_adv, form) se comprime a fracciones de gol en vez de sumarse
        # punto por punto como en baloncesto.
        expected_margin = (
            off_diff * 0.012
            + h_prof["home_adv"] * 0.08          # home_adv 2-8 (rango NBA) -> ~0.16-0.64 goles
            + (home_form - away_form) * 1.0      # form ya está en [0,1] -> directo en goles
            + (home_rest - away_rest) * 0.08
        )
        expected_margin = float(np.clip(expected_margin, *SOCCER_MARGIN_CLIP))

        expected_total = mean_tot + (h_prof["off_rating"] + a_prof["off_rating"] - 200) * 0.006
        expected_total = float(np.clip(expected_total, *SOCCER_TOTAL_CLIP))
    elif league in BASEBALL_LEAGUES:
        # Coeficientes propios de béisbol: la misma señal relativa (off_rating,
        # home_adv, form) se comprime a fracciones de carrera en vez de sumarse
        # punto por punto como en baloncesto. Es la misma corrección que ya se
        # hizo para fútbol, aplicada acá (antes KBO/MLB caían en la rama "else"
        # de abajo, calibrada para baloncesto).
        def_diff = a_prof["def_rating"] - h_prof["def_rating"]
        expected_margin = (
            off_diff * 0.035
            + def_diff * 0.035
            + h_prof["home_adv"] * 0.25
            + (home_form - away_form) * 3.0
            + (home_rest - away_rest) * 0.3
        )
        expected_margin = float(np.clip(expected_margin, *BASEBALL_MARGIN_CLIP))

        expected_total = mean_tot + (h_prof["off_rating"] + a_prof["off_rating"] - 200) * 0.05
        expected_total = float(np.clip(expected_total, *BASEBALL_TOTAL_CLIP))
    elif league in FOOTBALL_LEAGUES:
        # Coeficientes propios de fútbol americano: off_rating/def_rating y
        # form se comprimen a fracciones de punto de NFL en vez de sumarse
        # 1:1 como en baloncesto. home_adv (2-5, ya en escala de puntos de
        # ventaja de local) se deja casi intacto porque coincide de forma
        # razonable con el home field advantage real de la NFL (~2-3 pts).
        def_diff = a_prof["def_rating"] - h_prof["def_rating"]
        expected_margin = (
            off_diff * 0.28
            + def_diff * 0.28
            + h_prof["home_adv"] * 1.0
            + (home_form - away_form) * 8.0
            + (home_rest - away_rest) * 1.0
        )
        expected_margin = float(np.clip(expected_margin, *FOOTBALL_MARGIN_CLIP))

        expected_total = mean_tot + (h_prof["off_rating"] + a_prof["off_rating"] - 200) * 0.15
        expected_total = float(np.clip(expected_total, *FOOTBALL_TOTAL_CLIP))
    else:
        def_diff = a_prof["def_rating"] - h_prof["def_rating"]
        expected_margin = (
            off_diff * 0.3
            + def_diff * 0.3
            + h_prof["home_adv"]
            + (home_form - away_form) * 10
            + (home_rest - away_rest) * 1.5
        )
        expected_total = mean_tot + (h_prof["off_rating"] + a_prof["off_rating"] - 200) * 0.4

    return {"expected_margin": expected_margin, "expected_total": expected_total}


def margin_prob_scale(league: str) -> float:
    """
    Divisor del sigmoide que convierte margen esperado -> probabilidad
    implícita de victoria local. Se deriva de la volatilidad real de cada
    liga (LEAGUE_BASE_MARGINS) en vez de un '8.0' fijo pensado solo para
    baloncesto — con fútbol (std ~1.6-1.7), un margen esperado de apenas
    1-2 goles ya debe traducirse en una probabilidad bien inclinada, no
    quedarse cerca de 50/50 como pasaría si se dividiera entre 8.
    """
    _, std_mar = LEAGUE_BASE_MARGINS.get(league, (0.0, 8.0))
    return max(std_mar * 0.8, 0.3)


# Diferencia mínima (predicción del modelo vs línea de la casa) para
# recomendar Over/Under o un lado del hándicap en vez de "sin valor".
# Antes eran constantes fijas (2.0 goles, 1.5 de margen, 1.0 córner)
# pensadas para baloncesto/béisbol — aplicadas a fútbol (totales ~2.7
# goles) ese umbral casi nunca se alcanza, así que el pick prácticamente
# SIEMPRE caía en "PASS (LINE FAIR)" sin decir nunca Over ni Under.
LEAGUE_TOTAL_EDGE_THRESHOLD = {
    "MX": 0.4,
    "LCUP": 0.4,
    "MLB": 0.8,
    "KBO": 0.8,
    "NFL": 3.0,   # sobre un total ~43.5 pts, equivalente proporcional a los otros
}
LEAGUE_MARGIN_EDGE_THRESHOLD = {
    "MX": 0.35,
    "LCUP": 0.35,
    "MLB": 0.6,
    "KBO": 0.6,
    "NFL": 2.0,
}
LEAGUE_CORNERS_EDGE_THRESHOLD = {
    "MX": 0.6,
    "LCUP": 0.6,
}

def total_edge_threshold(league: str) -> float:
    return LEAGUE_TOTAL_EDGE_THRESHOLD.get(league, 2.0)

def margin_edge_threshold(league: str) -> float:
    return LEAGUE_MARGIN_EDGE_THRESHOLD.get(league, 1.5)

def corners_edge_threshold(league: str) -> float:
    return LEAGUE_CORNERS_EDGE_THRESHOLD.get(league, 1.0)


def generate_team_profiles(league: str) -> Dict[str, Dict]:
    teams = LEAGUE_TEAMS.get(league, LEAGUE_TEAMS["MLB"])
    np.random.seed(42 + _stable_seed(league) % 100)
    profiles = {}
    for team in teams:
        off_rating = np.random.normal(100, 10)
        def_rating = np.random.normal(100, 10)
        home_adv = np.random.uniform(2.0, 5.0)
        pace = np.random.normal(100, 5) if league == "WNBA" else np.random.normal(50, 5)
        pitching_era = np.random.normal(3.85, 0.65) if league in ["MLB", "KBO"] else 0.0
        profiles[team] = {
            "off_rating": round(off_rating, 2),
            "def_rating": round(def_rating, 2),
            "home_adv": round(home_adv, 2),
            "pace": round(pace, 2),
            "pitching_era": round(pitching_era, 2)
        }
    return profiles


def get_team_profiles_with_real_fallback(league: str) -> Dict[str, Dict]:
    """
    Perfiles de equipo PARA USAR EN PREDICCIONES: reales (ESPN, derivados de
    carreras/puntos anotados y recibidos en la temporada real) si hay
    partidos jugados suficientes; para KBO (que no está en ESPN) reales de
    TheSportsDB; si ninguna fuente real cubre un equipo, se completa con el
    perfil sintético (np.random) para que ningún equipo de LEAGUE_TEAMS
    quede sin perfil.

    Este es el punto ÚNICO de perfiles "listos para predecir". Antes,
    _enrich_fixture_with_profiles() -- la función que arma cada partido
    REAL que ve el usuario en el dashboard -- llamaba directo a
    generate_team_profiles(league), el generador 100% SINTÉTICO. Eso
    significaba que el off_rating/def_rating/home_adv de un partido real de
    MLB no tenían ninguna relación con qué tan bueno es ese equipo en la
    temporada real -- eran ruido reproducible (mismo partido, mismo
    número falso, pero sin señal real detrás). Con esas tres variables
    siendo ruido, una precisión cercana al 50% (moneda al aire) es
    exactamente lo esperable, no un fallo del ensemble en sí.

    Import de espn_historical hecho DENTRO de la función (no al tope del
    archivo) a propósito: espn_historical.py importa de data_generator.py,
    así que un import a nivel de módulo acá crearía un import circular.
    """
    profiles: Dict[str, Dict] = {}
    try:
        from app.ml.espn_historical import generate_team_profiles_from_espn
        profiles = generate_team_profiles_from_espn(league) or {}
    except Exception as e:
        logger.warning(f"No se pudieron obtener perfiles reales de ESPN para {league}: {e}")

    if not profiles and league == "KBO":
        try:
            from app.ml.kbo_thesportsdb import get_real_kbo_team_profiles
            profiles = get_real_kbo_team_profiles() or {}
        except Exception as e:
            logger.warning(f"No se pudieron obtener perfiles reales de KBO (TheSportsDB): {e}")

    if not profiles:
        return generate_team_profiles(league)

    if len(profiles) < len(LEAGUE_TEAMS.get(league, [])):
        merged = generate_team_profiles(league)
        merged.update(profiles)
        return merged

    return profiles


def get_real_form_and_rest_for_league(league: str, as_of_date: date) -> Dict[str, Dict]:
    """
    Forma/descanso reales por equipo (ver espn_historical.get_real_form_and_rest),
    listos para pasarle a _enrich_fixture_with_profiles(). Best-effort: si
    ESPN falla o la liga no tiene cobertura, devuelve {} y cada partido cae
    de vuelta al fallback aleatorio dentro de _enrich_fixture_with_profiles
    (nunca rompe la respuesta de /api/fixtures).

    Import local (no al tope del archivo) por la misma razón que en
    get_team_profiles_with_real_fallback: espn_historical.py importa de
    data_generator.py, un import a nivel de módulo acá sería circular.
    """
    try:
        from app.ml.espn_historical import get_real_form_and_rest
        return get_real_form_and_rest(league, as_of_date) or {}
    except Exception as e:
        logger.warning(f"No se pudo calcular forma/descanso reales para {league}: {e}")
        return {}


def get_real_odds_events_for_league(league: str) -> List[Dict]:
    """
    Eventos con cuotas reales de la liga (ver odds_api.get_real_odds_events),
    listos para pasarle a _enrich_fixture_with_profiles(). Best-effort: sin
    ODDS_API_KEY seteada, o si la liga no está en el catálogo de
    the-odds-api.com (LCUP, KBO), devuelve [] sin gastar créditos y cada
    partido sigue usando la cuota estimada de siempre.
    """
    try:
        from app.ml.odds_api import get_real_odds_events
        return get_real_odds_events(league) or []
    except Exception as e:
        logger.warning(f"No se pudieron obtener cuotas reales para {league}: {e}")
        return []


def generate_historical_dataset(league: str, n_samples: int = 1200,
                                 profiles: Optional[Dict[str, Dict]] = None) -> pd.DataFrame:
    """
    profiles: perfiles de equipo a usar en lugar de los sintéticos (np.random).
    Útil para ligas como KBO, donde sí hay datos reales (TheSportsDB) pero no
    hay histórico de partidos jugados vía API gratuita para entrenar directo.
    Equipos ausentes en `profiles` completan con el perfil sintético, para que
    nunca falte un equipo de LEAGUE_TEAMS.
    """
    np.random.seed(101 + _stable_seed(league) % 500)
    teams = LEAGUE_TEAMS.get(league, LEAGUE_TEAMS["MLB"])
    synthetic_profiles = generate_team_profiles(league)
    if profiles:
        merged = dict(synthetic_profiles)
        merged.update(profiles)
        profiles = merged
    else:
        profiles = synthetic_profiles
    mean_tot, std_tot = LEAGUE_BASE_TOTALS.get(league, (200.0, 10.0))
    _, std_mar = LEAGUE_BASE_MARGINS.get(league, (0.0, 8.0))

    rows = []
    for _ in range(n_samples):
        home_team, away_team = np.random.choice(teams, size=2, replace=False)
        h_prof = profiles[home_team]
        a_prof = profiles[away_team]

        # Features
        home_rest = np.random.choice([0, 1, 2, 3], p=[0.2, 0.5, 0.2, 0.1])
        away_rest = np.random.choice([0, 1, 2, 3], p=[0.25, 0.5, 0.2, 0.05])
        home_form = np.clip(np.random.normal(0.55, 0.2), 0.0, 1.0)
        away_form = np.clip(np.random.normal(0.50, 0.2), 0.0, 1.0)

        # Baseball specific
        h_pitcher_era = round(np.random.normal(h_prof["pitching_era"], 0.5), 2) if league in ["MLB", "KBO"] else 0.0
        a_pitcher_era = round(np.random.normal(a_prof["pitching_era"], 0.5), 2) if league in ["MLB", "KBO"] else 0.0

        # Derived Strength (sesgo base, ya calibrado por deporte)
        era_diff = (a_pitcher_era - h_pitcher_era) * 3.0 if league in ["MLB", "KBO"] else 0.0

        bias = estimate_matchup_bias(league, h_prof, a_prof, home_form, away_form, home_rest, away_rest)
        expected_margin = bias["expected_margin"] + era_diff
        actual_margin = expected_margin + np.random.normal(0, std_mar)

        # Total score
        combined_pace = (h_prof["pace"] + a_prof["pace"]) / 2.0
        pace_factor = (combined_pace - 100) * 0.5 if league == "WNBA" else 0
        expected_total = bias["expected_total"] - (era_diff * 0.5) + pace_factor
        actual_total = max(0.0 if league in SOCCER_LEAGUES else 1.0, expected_total + np.random.normal(0, std_tot))

        if league in ["MLB", "KBO"] + SOCCER_LEAGUES + FOOTBALL_LEAGUES:
            actual_margin = np.round(actual_margin)
            actual_total = np.round(actual_total, 1)

        home_win = 1 if actual_margin > 0 else 0

        # Bookmaker lines
        implied_home_prob = 1 / (1 + np.exp(-expected_margin / margin_prob_scale(league)))
        sb_home_odds = round(1.0 / implied_home_prob if implied_home_prob > 0.05 else 15.0, 2)
        sb_away_odds = round(1.0 / (1 - implied_home_prob) if implied_home_prob < 0.95 else 15.0, 2)
        sb_spread = round(-expected_margin * 0.9, 1)
        sb_total = round(expected_total, 1)

        # Tiros de esquina totales (solo fútbol / MX, LCUP) — equipos más ofensivos
        # tienden a generar levemente más córners
        total_corners = None
        sb_corners_total = None
        if league in SOCCER_LEAGUES:
            mean_corn, std_corn = LEAGUE_BASE_CORNERS.get(league, (10.0, 3.0))
            corner_bias = (h_prof["off_rating"] + a_prof["off_rating"] - 200) * 0.03
            expected_corners = mean_corn + corner_bias
            total_corners = float(max(0, np.round(expected_corners + np.random.normal(0, std_corn))))
            sb_corners_total = round(expected_corners, 1)

        rows.append({
            "league": league,
            "home_team": home_team,
            "away_team": away_team,
            "home_off_rating": h_prof["off_rating"],
            "away_off_rating": a_prof["off_rating"],
            "home_def_rating": h_prof["def_rating"],
            "away_def_rating": a_prof["def_rating"],
            "home_adv": h_prof["home_adv"],
            "home_rest": home_rest,
            "away_rest": away_rest,
            "home_form": round(home_form, 2),
            "away_form": round(away_form, 2),
            "h_pitcher_era": h_pitcher_era,
            "a_pitcher_era": a_pitcher_era,
            "pace": h_prof["pace"],
            # Targets
            "home_win": home_win,
            "margin": round(actual_margin, 2),
            "total_points": round(actual_total, 2),
            "total_corners": total_corners,  # None para ligas que no son de fútbol
            # Odds
            "sb_home_odds": sb_home_odds,
            "sb_away_odds": sb_away_odds,
            "sb_spread": sb_spread,
            "sb_total": sb_total,
            "sb_corners_total": sb_corners_total
        })

    return pd.DataFrame(rows)

def _build_explanation(home_team: str, away_team: str, h_prof: Dict, a_prof: Dict,
                       home_form: float, away_form: float, form_rest_is_real: bool,
                       home_rest: int, away_rest: int,
                       h_era: float, a_era: float, era_is_real: bool, league: str) -> List[str]:
    """
    Explicación en lenguaje natural de las señales más fuertes detrás de la
    predicción -- reglas simples y transparentes sobre los mismos features
    que ya usa el modelo (nada nuevo, solo lo hace legible). Máximo 4
    razones, ordenadas por qué tan grande es la diferencia entre equipos,
    para no saturar la tarjeta con ruido de diferencias chicas.
    """
    candidates = []  # (magnitud, texto) -- se ordena por magnitud antes de recortar a 4

    form_diff = home_form - away_form
    if abs(form_diff) >= 0.12:
        leader, pct = (home_team, home_form) if form_diff > 0 else (away_team, away_form)
        tag = "real" if form_rest_is_real else "estimada"
        candidates.append((abs(form_diff), f"{leader} llega con mejor forma reciente ({round(pct * 100)}% en sus últimos partidos, {tag})"))

    rest_diff = home_rest - away_rest
    if abs(rest_diff) >= 2:
        leader = home_team if rest_diff > 0 else away_team
        candidates.append((abs(rest_diff) * 0.1, f"{leader} llega con más días de descanso"))

    off_diff = h_prof["off_rating"] - a_prof["off_rating"]
    if abs(off_diff) >= 5:
        leader, val = (home_team, h_prof["off_rating"]) if off_diff > 0 else (away_team, a_prof["off_rating"])
        candidates.append((abs(off_diff) * 0.05, f"{leader} tiene mejor ataque esta temporada (rating {round(val, 1)})"))

    def_diff = a_prof["def_rating"] - h_prof["def_rating"]  # positivo = home tiene mejor defensa (permite menos)
    if abs(def_diff) >= 5:
        leader, val = (home_team, h_prof["def_rating"]) if def_diff > 0 else (away_team, a_prof["def_rating"])
        candidates.append((abs(def_diff) * 0.05, f"{leader} tiene mejor defensa esta temporada (rating {round(val, 1)})"))

    if league in BASEBALL_LEAGUES and h_era and a_era:
        era_diff = a_era - h_era  # positivo = home tiene ERA más bajo (mejor)
        if abs(era_diff) >= 0.4:
            leader, val = (home_team, h_era) if era_diff > 0 else (away_team, a_era)
            tag = "real" if era_is_real else "estimado"
            candidates.append((abs(era_diff), f"Abridor de {leader} con mejor efectividad (ERA {val}, {tag})"))

    if h_prof["home_adv"] >= 3.5:
        candidates.append((h_prof["home_adv"] * 0.05, f"{home_team} tiene una ventaja de local marcada esta temporada"))

    candidates.sort(key=lambda c: c[0], reverse=True)
    reasons = [text for _, text in candidates[:4]]

    if not reasons:
        reasons.append("Partido parejo — ninguna señal domina claramente entre estos dos equipos")

    return reasons


def _enrich_fixture_with_profiles(home_team: str, away_team: str, league: str,
                                  date_str: str, idx: int,
                                  fixture_id: str = None,
                                  time_str: str = "TBD",
                                  source: str = "Simulado",
                                  home_pitcher_era_real=None,
                                  away_pitcher_era_real=None,
                                  profiles: Optional[Dict[str, Dict]] = None,
                                  form_rest: Optional[Dict[str, Dict]] = None,
                                  odds_events: Optional[List[Dict]] = None,
                                  **kwargs) -> Dict:
    """
    Dado un partido (home_team vs away_team) genera los features que necesita
    el modelo ML y las líneas de casas de apuestas.

    profiles: perfiles de equipo YA resueltos (reales de ESPN/TheSportsDB
        con fallback sintético, ver get_team_profiles_with_real_fallback)
        para reutilizar entre todos los partidos de una misma llamada a
        get_upcoming_fixtures() -- evita recalcular/refetchear perfiles por
        cada fixture. Si no se pasa, se resuelven acá con la misma
        prioridad real->sintético (pensado para llamar esta función suelta,
        ej. tests o scripts).
    form_rest: forma/descanso YA resueltos (reales de ESPN, ver
        get_real_form_and_rest_for_league) -- mismo motivo que profiles.
        Si un equipo no tiene suficiente muestra real (< 3 partidos), cae
        al fallback aleatorio de siempre para ESE equipo puntual.
    odds_events: eventos con cuotas reales YA resueltos (the-odds-api.com,
        ver get_real_odds_events_for_league) -- si hay match para este
        partido, sb_home_odds/sb_away_odds/sb_spread/sb_total se
        reemplazan por la línea real; si no, quedan las estimadas.
    """
    if profiles is None:
        profiles = get_team_profiles_with_real_fallback(league)

    # Semilla determinista por partido para que los valores aleatorios de
    # fallback sean reproducibles
    seed = _stable_seed(f"{date_str}{home_team}{away_team}") % (2**31)
    rng = np.random.default_rng(seed)

    h_prof = profiles.get(home_team, {"off_rating": 100, "def_rating": 100, "home_adv": 3.0, "pace": 100, "pitching_era": 3.85})
    a_prof = profiles.get(away_team, {"off_rating": 100, "def_rating": 100, "home_adv": 0.0, "pace": 100, "pitching_era": 3.95})

    # --- Forma/descanso: usar los reales de ESPN si hay muestra suficiente,
    # si no, el fallback aleatorio (equipos de expansión, ligas sin
    # cobertura ESPN, arranque de temporada sin historial todavía, etc.) ---
    h_fr = (form_rest or {}).get(home_team)
    a_fr = (form_rest or {}).get(away_team)
    form_rest_is_real = bool(h_fr and a_fr and h_fr.get("games_sampled", 0) >= 3 and a_fr.get("games_sampled", 0) >= 3)

    if h_fr and h_fr.get("games_sampled", 0) >= 3:
        home_rest, home_form = h_fr["rest"], h_fr["form"]
    else:
        home_rest = int(rng.choice([0, 1, 2, 3], p=[0.2, 0.5, 0.2, 0.1]))
        home_form = round(float(np.clip(rng.normal(0.58, 0.15), 0.1, 0.95)), 2)

    if a_fr and a_fr.get("games_sampled", 0) >= 3:
        away_rest, away_form = a_fr["rest"], a_fr["form"]
    else:
        away_rest = int(rng.choice([0, 1, 2, 3], p=[0.25, 0.5, 0.2, 0.05]))
        away_form = round(float(np.clip(rng.normal(0.50, 0.15), 0.1, 0.95)), 2)

    h_pitcher = f"Pitcher {home_team[:3].upper()}" if league in ["MLB", "KBO"] else "N/A"
    a_pitcher = f"Pitcher {away_team[:3].upper()}" if league in ["MLB", "KBO"] else "N/A"

    # --- ERA: usar la real de ESPN si está disponible, si no, estimar ---
    era_is_real = False
    if league in ["MLB", "KBO"]:
        if home_pitcher_era_real is not None and away_pitcher_era_real is not None:
            h_era = round(float(home_pitcher_era_real), 2)
            a_era = round(float(away_pitcher_era_real), 2)
            era_is_real = True
        else:
            h_era = round(float(rng.normal(h_prof.get("pitching_era", 3.85), 0.5)), 2)
            a_era = round(float(rng.normal(a_prof.get("pitching_era", 3.95), 0.5)), 2)
    else:
        h_era = 0.0
        a_era = 0.0

    bias = estimate_matchup_bias(league, h_prof, a_prof, home_form, away_form, home_rest, away_rest)
    exp_margin = bias["expected_margin"]
    exp_total = bias["expected_total"]

    # El dataset de entrenamiento (generate_historical_dataset) SÍ suma el
    # diferencial de ERA al sesgo esperado -- acá faltaba, así que la línea
    # en vivo ignoraba por completo al pitcher probable. Se usa el mismo peso
    # (3.0) para que ambos caminos queden coherentes.
    if league in BASEBALL_LEAGUES:
        era_diff = (a_era - h_era) * 3.0
        exp_margin = float(np.clip(exp_margin + era_diff, *BASEBALL_MARGIN_CLIP))
        exp_total = float(np.clip(exp_total - era_diff * 0.5, *BASEBALL_TOTAL_CLIP))

    sb_spread = round(-exp_margin, 1)
    sb_total = round(exp_total, 1)

    p_home = 1 / (1 + np.exp(-exp_margin / margin_prob_scale(league)))
    sb_home_odds = round(float(1.0 / p_home if p_home > 0.05 else 12.0), 2)
    sb_away_odds = round(float(1.0 / (1 - p_home) if p_home < 0.95 else 12.0), 2)

    # --- Cuotas reales (the-odds-api.com) si hay match para este partido --
    # si no, quedan las estimadas de arriba. Nunca puede romper la
    # respuesta: cualquier error acá se ignora y sigue con la estimada.
    odds_source = "estimado"
    if odds_events:
        try:
            from app.ml.odds_api import match_fixture_odds
            real_odds = match_fixture_odds(odds_events, home_team, away_team)
            if real_odds:
                sb_home_odds = real_odds["sb_home_odds"]
                sb_away_odds = real_odds["sb_away_odds"]
                sb_spread = real_odds.get("sb_spread", sb_spread)
                sb_total = real_odds.get("sb_total", sb_total)
                odds_source = "real"
        except Exception as e:
            logger.warning(f"No se pudo aplicar cuota real para {home_team} vs {away_team}: {e}")

    # Línea estimada de córners totales — solo aplica a ligas de fútbol (MX, LCUP)
    sb_corners_total = None
    if league in SOCCER_LEAGUES:
        mean_corn, _ = LEAGUE_BASE_CORNERS.get(league, (10.0, 3.0))
        corner_bias = (h_prof["off_rating"] + a_prof["off_rating"] - 200) * 0.03
        sb_corners_total = round(float(mean_corn + corner_bias), 1)

    explanation = _build_explanation(
        home_team, away_team, h_prof, a_prof,
        home_form, away_form, form_rest_is_real,
        home_rest, away_rest, h_era, a_era, era_is_real, league,
    )

    return {
        "fixture_id": fixture_id or f"FIX-{league}-{date_str}-{idx}",
        "date": date_str,
        "time": time_str,
        "league": league,
        "home_team": home_team,
        "away_team": away_team,
        "home_rest": home_rest,
        "away_rest": away_rest,
        "home_form": home_form,
        "away_form": away_form,
        "form_rest_is_real": form_rest_is_real,   # badge de transparencia en el frontend
        "h_pitcher": h_pitcher,
        "a_pitcher": a_pitcher,
        "h_pitcher_era": h_era,
        "a_pitcher_era": a_era,
        "pitcher_era_is_real": era_is_real,   # útil para mostrar un badge en el frontend
        "home_off_rating": h_prof["off_rating"],
        "away_off_rating": a_prof["off_rating"],
        "home_def_rating": h_prof["def_rating"],
        "away_def_rating": a_prof["def_rating"],
        "home_adv": h_prof["home_adv"],
        "pace": h_prof["pace"],
        "sb_home_odds": sb_home_odds,
        "sb_away_odds": sb_away_odds,
        "sb_spread": sb_spread,
        "sb_total": sb_total,
        "sb_corners_total": sb_corners_total,
        "odds_source": odds_source,   # "real" (the-odds-api.com) o "estimado"
        "explanation": explanation,   # razones en lenguaje natural para el panel "¿Por qué esta predicción?"
        "source": source,
        "home_logo": kwargs.get("home_logo", ""),
        "away_logo": kwargs.get("away_logo", ""),
    }


def get_upcoming_fixtures(league: str, target_date: Optional[date] = None, count: int = 8,
                           allow_simulated_fallback: bool = False) -> List[Dict]:
    """
    Obtiene los partidos para la fecha indicada.
    1. Intenta ESPN (o TheSportsDB para KBO) para obtener partidos REALES.
    2. Si no hay datos reales, por defecto devuelve lista VACÍA — el
       frontend (DailyFixtures.jsx) muestra un mensaje de "sin partidos
       reales para esta fecha" en vez de datos inventados. Antes acá se
       caía a partidos 100% simulados, lo cual es engañoso: parecía que
       había partidos programados cuando en realidad no los hay.

    allow_simulated_fallback: True restaura el comportamiento anterior
        (generar partidos simulados). Solo pensado para demos/pruebas
        locales — no se usa por defecto desde /api/fixtures.
    target_date: fecha objetivo (default = mañana).
    """
    if target_date is None:
        target_date = date.today() + timedelta(days=1)

    date_str = target_date.strftime("%Y-%m-%d")

    # --- Intentar partidos reales primero ---
    try:
        from app.ml.sports_api import get_real_fixtures
        real_fixtures = get_real_fixtures(league, target_date)
    except Exception:
        real_fixtures = []

    if real_fixtures:
        # Perfiles reales (ESPN / TheSportsDB, con fallback sintético) UNA
        # sola vez por request -- antes cada partido llamaba a
        # generate_team_profiles(league) por su cuenta (100% sintético),
        # ver get_team_profiles_with_real_fallback().
        profiles = get_team_profiles_with_real_fallback(league)

        # Forma/descanso reales y cuotas reales -- también UNA sola vez por
        # request (no por partido): un solo fetch de ESPN histórico y un
        # solo request a the-odds-api.com traen los datos de TODOS los
        # partidos del día de esta liga de una vez.
        form_rest = get_real_form_and_rest_for_league(league, target_date)
        odds_events = get_real_odds_events_for_league(league)

        enriched = []
        for idx, fix in enumerate(real_fixtures):
            enriched.append(_enrich_fixture_with_profiles(
                home_team=fix["home_team"],
                away_team=fix["away_team"],
                league=league,
                date_str=date_str,
                idx=idx,
                fixture_id=fix["fixture_id"],
                time_str=fix.get("time", "TBD"),
                source=fix.get("source", "API"),
                home_logo=fix.get("home_logo", ""),
                away_logo=fix.get("away_logo", ""),
                home_pitcher_era_real=fix.get("home_pitcher_era_real"),
                away_pitcher_era_real=fix.get("away_pitcher_era_real"),
                profiles=profiles,
                form_rest=form_rest,
                odds_events=odds_events,
            ))
        return enriched

    if not allow_simulated_fallback:
        logger.info(
            f"Sin partidos reales para {league} el {date_str} — no se generan "
            f"partidos simulados (allow_simulated_fallback=False), se devuelve lista vacía."
        )
        return []

    # --- Fallback: partidos simulados (solo si se pide explícitamente) ---
    rng = np.random.default_rng(_stable_seed(f"{date_str}{league}") % (2**31))
    teams = LEAGUE_TEAMS.get(league, LEAGUE_TEAMS["MLB"])
    fixtures = []
    used_teams: set = set()

    for i in range(count):
        available = [t for t in teams if t not in used_teams]
        if len(available) < 2:
            used_teams.clear()
            available = list(teams)
        chosen = rng.choice(available, size=2, replace=False)
        home_team, away_team = str(chosen[0]), str(chosen[1])
        used_teams.add(home_team)
        used_teams.add(away_team)

        fixtures.append(_enrich_fixture_with_profiles(
            home_team=home_team,
            away_team=away_team,
            league=league,
            date_str=date_str,
            idx=i,
            source="Simulado",
        ))

    return fixtures



# Alias para compatibilidad con código existente que llama a get_2026_upcoming_fixtures
def get_2026_upcoming_fixtures(league: str, count: int = 8) -> List[Dict]:
    return get_upcoming_fixtures(league, count=count)


# ---------------------------------------------------------------------
# Mezcla suave entre datos reales (ESPN) y sintéticos
# ---------------------------------------------------------------------
# Antes, generate_historical_dataset_from_espn() exigía >=30 partidos reales
# o devolvía un DataFrame vacío -> el llamador caía 100% al dataset
# sintético. Eso producía un salto brusco de metodología de entrenamiento
# apenas se cruzaba ese umbral (ej. Leagues Cup pasando de 29 a 30 partidos
# jugados), lo que podía voltear la predicción de un mismo partido de un
# deploy a otro sin que el partido en sí hubiera cambiado.
#
# blend_real_and_synthetic() reemplaza ese salto por una rampa continua:
# con pocos partidos reales (<MIN_REAL_GAMES) se usa 100% sintético igual
# que antes; con muchos (>=FULL_REAL_GAMES) se usa 100% real igual que
# antes; en el rango intermedio se mezclan ambos con un peso que crece
# proporcionalmente a la cantidad de partidos reales disponibles, así que
# cada partido nuevo jugado mueve el modelo un poco, no todo de golpe.
MIN_REAL_GAMES = 8      # por debajo de esto, el real es demasiado ruidoso -> 100% sintético
FULL_REAL_GAMES = 30    # a partir de esto, el real ya es representativo -> 100% real


def blend_real_and_synthetic(league: str, df_real: pd.DataFrame, n_samples: int = 1000,
                              extra_profiles: Optional[Dict[str, Dict]] = None) -> pd.DataFrame:
    n_real = len(df_real)

    if n_real >= FULL_REAL_GAMES:
        return df_real

    if n_real < MIN_REAL_GAMES:
        return generate_historical_dataset(league, n_samples=n_samples, profiles=extra_profiles)

    weight_real = (n_real - MIN_REAL_GAMES) / (FULL_REAL_GAMES - MIN_REAL_GAMES)  # 0..1 continuo

    synth = generate_historical_dataset(league, n_samples=n_samples, profiles=extra_profiles)

    # Repetimos los partidos reales (con jitter leve en el ruido, ya
    # implícito en total_points/margin reales) para que su peso relativo
    # en el dataset combinado sea proporcional a weight_real, en vez de
    # quedar diluidos 1-a-1 frente a cientos de filas sintéticas.
    target_real_rows = max(n_real, int(round(weight_real * n_samples)))
    repeats = max(1, -(-target_real_rows // n_real))  # ceil division
    df_real_boosted = pd.concat([df_real] * repeats, ignore_index=True).iloc[:target_real_rows]

    n_synth_keep = max(1, int(round((1.0 - weight_real) * n_samples)))
    seed = _stable_seed(f"blend-{league}") % (2**31)
    synth_sample = synth.sample(
        n=min(n_synth_keep, len(synth)), random_state=seed, replace=n_synth_keep > len(synth)
    )

    blended = pd.concat([df_real_boosted, synth_sample], ignore_index=True)
    logger.info(
        f"{league}: dataset mezclado -> {n_real} partidos reales "
        f"(peso {weight_real:.2f}) + {len(synth_sample)} filas sintéticas de relleno"
    )
    return blended.reset_index(drop=True)
