import numpy as np
import pandas as pd
from datetime import date, timedelta
from typing import Dict, List, Optional

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
    "MX": _MX_TEAMS
}

LEAGUE_BASE_TOTALS = {
    "LCUP": (2.9, 1.6),     # Goles totales por partido (fútbol, torneo eliminatorio de verano)
    "MLB": (8.5, 2.1),
    "WNBA": (163.5, 9.5),
    "KBO": (9.8, 2.4),
    "MX": (2.6, 1.4)        # Goles totales por partido (fútbol)
}

LEAGUE_BASE_MARGINS = {
    "LCUP": (0.0, 1.7),     # Diferencia de goles
    "MLB": (0.0, 3.2),
    "WNBA": (0.0, 9.8),
    "KBO": (0.0, 3.5),
    "MX": (0.0, 1.6)        # Diferencia de goles
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
}
LEAGUE_MARGIN_EDGE_THRESHOLD = {
    "MX": 0.35,
    "LCUP": 0.35,
    "MLB": 0.6,
    "KBO": 0.6,
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
    np.random.seed(42 + hash(league) % 100)
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

def generate_historical_dataset(league: str, n_samples: int = 1200,
                                 profiles: Optional[Dict[str, Dict]] = None) -> pd.DataFrame:
    """
    profiles: perfiles de equipo a usar en lugar de los sintéticos (np.random).
    Útil para ligas como KBO, donde sí hay datos reales (TheSportsDB) pero no
    hay histórico de partidos jugados vía API gratuita para entrenar directo.
    Equipos ausentes en `profiles` completan con el perfil sintético, para que
    nunca falte un equipo de LEAGUE_TEAMS.
    """
    np.random.seed(101 + hash(league) % 500)
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

        if league in ["MLB", "KBO"] + SOCCER_LEAGUES:
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

def _enrich_fixture_with_profiles(home_team: str, away_team: str, league: str,
                                  date_str: str, idx: int,
                                  fixture_id: str = None,
                                  time_str: str = "TBD",
                                  source: str = "Simulado",
                                  home_pitcher_era_real=None,
                                  away_pitcher_era_real=None,
                                  **kwargs) -> Dict:
    """
    Dado un partido (home_team vs away_team) genera los features que necesita
    el modelo ML y las líneas de casas de apuestas estimadas.
    """
    profiles = generate_team_profiles(league)

    # Semilla determinista por partido para que los valores sean reproducibles
    seed = hash(f"{date_str}{home_team}{away_team}") % (2**31)
    rng = np.random.default_rng(seed)

    h_prof = profiles.get(home_team, {"off_rating": 100, "def_rating": 100, "home_adv": 3.0, "pace": 100, "pitching_era": 3.85})
    a_prof = profiles.get(away_team, {"off_rating": 100, "def_rating": 100, "home_adv": 0.0, "pace": 100, "pitching_era": 3.95})

    home_rest = int(rng.choice([0, 1, 2, 3], p=[0.2, 0.5, 0.2, 0.1]))
    away_rest = int(rng.choice([0, 1, 2, 3], p=[0.25, 0.5, 0.2, 0.05]))
    home_form = round(float(np.clip(rng.normal(0.58, 0.15), 0.1, 0.95)), 2)
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

    # Línea estimada de córners totales — solo aplica a ligas de fútbol (MX, LCUP)
    sb_corners_total = None
    if league in SOCCER_LEAGUES:
        mean_corn, _ = LEAGUE_BASE_CORNERS.get(league, (10.0, 3.0))
        corner_bias = (h_prof["off_rating"] + a_prof["off_rating"] - 200) * 0.03
        sb_corners_total = round(float(mean_corn + corner_bias), 1)

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
        "source": source,
        "home_logo": kwargs.get("home_logo", ""),
        "away_logo": kwargs.get("away_logo", ""),
    }


def get_upcoming_fixtures(league: str, target_date: Optional[date] = None, count: int = 8) -> List[Dict]:
    """
    Obtiene los partidos para la fecha indicada.
    1. Intenta ESPN para obtener partidos REALES.
    2. Si no hay datos reales, genera partidos SIMULADOS como fallback.
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
        # Enriquecer los partidos reales con perfiles ML, líneas estimadas y ERA real si existe
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
            ))
        return enriched

    # --- Fallback: partidos simulados ---
    rng = np.random.default_rng(hash(f"{date_str}{league}") % (2**31))
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
