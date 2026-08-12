"""
espn_historical.py — Obtiene RESULTADOS REALES de partidos ya jugados desde ESPN
y construye un dataset de entrenamiento histórico a partir de ellos, en vez de
datos sintéticos (np.random). Incluye ERA REAL del abridor por partido (MLB).

Reemplaza:
  - generate_team_profiles()      -> generate_team_profiles_from_espn()
  - generate_historical_dataset() -> generate_historical_dataset_from_espn()

IMPORTANTE sobre el ERA — cómo se evita el data leakage:
  No usamos el ERA que el pitcher tuvo EN ese partido para predecir ese mismo
  partido (eso sería filtrar el resultado). En vez de eso, recorremos los
  partidos en orden cronológico y para cada uno usamos el ERA ACUMULADO del
  pitcher hasta ANTES de ese partido (earned runs acumulados * 9 / innings
  acumuladas). Recién después de calcular la fila, sumamos las stats de ESE
  partido al acumulado del pitcher, para el próximo partido.

Limitaciones honestas:
  - Solo MLB tiene ERA real disponible vía ESPN (KBO no está en ESPN, NBA/WNBA
    no aplica).
  - Requiere 1 request adicional al boxscore POR CADA partido histórico para
    identificar al abridor y sus stats de ese juego -> es lento para rangos
    grandes. Usa max_games_for_era para limitar, o cachea resultados tú mismo.
  - El esquema de la API de ESPN es NO oficial y puede cambiar sin aviso;
    el parseo del boxscore usa heurísticas (mayor IP del partido = abridor,
    si no hay un flag explícito "starter").
"""

import httpx
import logging
import os
import time
import threading
import numpy as np
import pandas as pd
from datetime import date, datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from app.ml.sports_api import ESPN_ENDPOINTS, normalize_team
from app.ml.data_generator import estimate_matchup_bias, margin_prob_scale

logger = logging.getLogger(__name__)

MLB_SUMMARY_URL = "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/summary"

# Cuántos días hacia atrás buscar partidos TERMINADOS, por liga. 180 días
# funciona bien para ligas que juegan casi todo el año (MLB, WNBA, MX,
# LCUP), pero la NFL tiene una offseason larga (~feb-ago): consultada en
# pretemporada (como ahora, agosto), una ventana de 180 días cae casi
# entera en offseason y solo encuentra 0-1 partidos, cayendo al fallback
# sintético aunque exista una temporada regular + playoffs completa recién
# terminada en enero/febrero. 400 días asegura cubrir toda la temporada
# anterior de la NFL sin importar en qué mes del año se consulte.
LEAGUE_LOOKBACK_DAYS: Dict[str, int] = {
    "NFL": 400,
}
DEFAULT_LOOKBACK_DAYS = 180

# Ligas de fútbol cubiertas -> slug ESPN usado en la URL del summary (boxscore)
# LCUP usa el mismo slug que sports_api.py (concacaf.leagues.cup) — antes
# faltaba acá, lo que significaba que la Leagues Cup nunca traía córners
# reales de ESPN para su dataset histórico (aunque sí traía los partidos).
SOCCER_LEAGUE_SLUGS = {
    "MX": "mex.1",
    "LCUP": "concacaf.leagues.cup",
}


def fetch_match_corners(event_id: str, league_slug: str, client: httpx.Client) -> Optional[Tuple[float, float]]:
    """
    Devuelve (corners_local, corners_visitante) de un partido de fútbol YA
    JUGADO, leyendo el boxscore de ESPN (stat 'wonCorners' por equipo).
    Retorna None si ESPN no publicó ese stat para este partido (pasa con
    partidos antiguos o de ligas donde ESPN no trackea córners).
    """
    url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league_slug}/summary"
    try:
        resp = client.get(url, params={"event": event_id})
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.warning(f"No se pudo obtener boxscore de córners de {event_id}: {e}")
        return None

    try:
        teams_stats = data.get("boxscore", {}).get("teams", [])
        corners: Dict[str, float] = {}
        for team_block in teams_stats:
            home_away = team_block.get("homeAway")
            stats = team_block.get("statistics", [])
            corner_stat = next(
                (s for s in stats if (s.get("name") or "").lower() == "woncorners"),
                None
            )
            # Fallback por si el nombre exacto del stat varía entre eventos
            if corner_stat is None:
                corner_stat = next(
                    (s for s in stats if "corner" in (s.get("name") or "").lower()),
                    None
                )
            if corner_stat is None or home_away not in ("home", "away"):
                continue
            try:
                corners[home_away] = float(corner_stat.get("displayValue", corner_stat.get("value", 0)))
            except (TypeError, ValueError):
                continue

        if "home" in corners and "away" in corners:
            return corners["home"], corners["away"]
    except Exception as e:
        logger.warning(f"Error parseando córners de {event_id}: {e}")

    return None


# ---------------------------------------------------------------------------
# 1. Descarga de partidos terminados (resultados reales)
# ---------------------------------------------------------------------------

def _parse_completed_event(ev: Dict, league: str) -> Optional[Dict]:
    """Extrae marcador final + event_id de un evento ESPN ya jugado."""
    try:
        status = ev.get("status", {}).get("type", {})
        if not status.get("completed", False):
            return None

        competitions = ev.get("competitions", [{}])[0]
        competitors = competitions.get("competitors", [])

        home_comp = next((c for c in competitors if c.get("homeAway") == "home"), None)
        away_comp = next((c for c in competitors if c.get("homeAway") == "away"), None)
        if not home_comp or not away_comp:
            return None

        home_raw = home_comp.get("team", {}).get("displayName", "")
        away_raw = away_comp.get("team", {}).get("displayName", "")
        home_score = home_comp.get("score")
        away_score = away_comp.get("score")

        if not home_raw or not away_raw or home_score is None or away_score is None:
            return None

        raw_date = ev.get("date", "")
        game_date = raw_date.split("T")[0] if "T" in raw_date else raw_date

        return {
            "event_id": str(ev.get("id", "")),
            "date": game_date,
            "league": league,
            "home_team": normalize_team(home_raw),
            "away_team": normalize_team(away_raw),
            "home_score": float(home_score),
            "away_score": float(away_score),
        }
    except Exception as e:
        logger.warning(f"Error parseando evento histórico ESPN: {e}")
        return None


def fetch_completed_games(league: str, start_date: date, end_date: date) -> List[Dict]:
    """Descarga partidos TERMINADOS de ESPN entre start_date y end_date (inclusive)."""
    url = ESPN_ENDPOINTS.get(league)
    if not url:
        logger.info(f"{league} no tiene endpoint ESPN -> sin histórico real disponible")
        return []

    games: List[Dict] = []
    current = start_date

    with httpx.Client(timeout=15.0, verify=False) as client:
        while current <= end_date:
            chunk_end = min(current + timedelta(days=29), end_date)
            date_range = f"{current.strftime('%Y%m%d')}-{chunk_end.strftime('%Y%m%d')}"

            try:
                resp = client.get(url, params={"dates": date_range, "limit": 1000})
                resp.raise_for_status()
                data = resp.json()
            except httpx.TimeoutException:
                logger.error(f"Timeout ESPN histórico {league} {date_range}")
                current = chunk_end + timedelta(days=1)
                continue
            except httpx.HTTPError as e:
                logger.error(f"Error HTTP ESPN histórico {league} {date_range}: {e}")
                current = chunk_end + timedelta(days=1)
                continue

            for ev in data.get("events", []):
                parsed = _parse_completed_event(ev, league)
                if parsed:
                    games.append(parsed)

            current = chunk_end + timedelta(days=1)

    logger.info(f"ESPN histórico: {len(games)} partidos terminados para {league} "
                f"entre {start_date} y {end_date}")
    return games


# ---------------------------------------------------------------------------
# 1.5 Cache de partidos terminados -- ANTES, generate_team_profiles_from_espn()
#     y get_real_form_and_rest() hacían CADA UNA su propio fetch_completed_games
#     sobre ventanas de fechas que en la práctica coinciden casi siempre
#     (ambas normalizan end_date a hoy más abajo), así que /api/fixtures
#     descargaba el mismo histórico de ESPN dos veces en cada request, sin
#     cachear nada entre requests tampoco. Este wrapper resuelve ambos
#     problemas: dedupe dentro del mismo request Y cache entre requests.
# ---------------------------------------------------------------------------

_completed_games_cache: Dict[str, Dict] = {}
_completed_games_cache_lock = threading.Lock()
COMPLETED_GAMES_CACHE_TTL_MINUTES = float(os.environ.get("COMPLETED_GAMES_CACHE_TTL_MINUTES", "30"))


def fetch_completed_games_cached(league: str, start_date: date, end_date: date) -> List[Dict]:
    """Misma firma que fetch_completed_games(), pero cacheada
    COMPLETED_GAMES_CACHE_TTL_MINUTES minutos por (liga, start, end) exactos.
    Con TTL=30min, varias cargas del dashboard en esa ventana reusan el
    mismo histórico en vez de volver a pegarle a ESPN cada vez."""
    key = f"{league}:{start_date.isoformat()}:{end_date.isoformat()}"

    with _completed_games_cache_lock:
        cached = _completed_games_cache.get(key)
        if cached and (datetime.now(timezone.utc) - cached["fetched_at"]) < timedelta(minutes=COMPLETED_GAMES_CACHE_TTL_MINUTES):
            return cached["games"]

    games = fetch_completed_games(league, start_date, end_date)

    with _completed_games_cache_lock:
        _completed_games_cache[key] = {"fetched_at": datetime.now(timezone.utc), "games": games}

    return games


# ---------------------------------------------------------------------------
# 2. Ratings de equipo reales
# ---------------------------------------------------------------------------

def generate_team_profiles_from_espn(league: str, lookback_days: Optional[int] = None) -> Dict[str, Dict]:
    """Calcula ratings ofensivo/defensivo/home_adv/pace REALES de la temporada."""
    if lookback_days is None:
        lookback_days = LEAGUE_LOOKBACK_DAYS.get(league, DEFAULT_LOOKBACK_DAYS)
    end = date.today()
    start = end - timedelta(days=lookback_days)
    games = fetch_completed_games_cached(league, start, end)

    if not games:
        logger.warning(f"Sin partidos reales para calcular perfiles de {league}")
        return {}

    df = pd.DataFrame(games)
    scored, allowed, home_margins = {}, {}, {}
    for _, g in df.iterrows():
        h, a = g["home_team"], g["away_team"]
        hs, aws = g["home_score"], g["away_score"]
        scored.setdefault(h, []).append(hs)
        scored.setdefault(a, []).append(aws)
        allowed.setdefault(h, []).append(aws)
        allowed.setdefault(a, []).append(hs)
        home_margins.setdefault(h, []).append(hs - aws)

    all_teams = set(scored.keys())
    league_avg_pts = float(np.mean([v for vals in scored.values() for v in vals]))

    profiles = {}
    for team in all_teams:
        avg_scored = float(np.mean(scored[team]))
        avg_allowed = float(np.mean(allowed[team]))
        avg_home_margin = float(np.mean(home_margins.get(team, [3.0])))
        pace = (avg_scored + avg_allowed) / 2.0

        profiles[team] = {
            "off_rating": round(100.0 + (avg_scored - league_avg_pts), 2),
            "def_rating": round(100.0 + (avg_allowed - league_avg_pts), 2),
            "home_adv": round(float(np.clip(avg_home_margin, 0.5, 8.0)), 2),
            "pace": round(pace, 2),
            "pitching_era": 0.0,
            "games_sampled": len(scored[team]),
        }

    return profiles


# ---------------------------------------------------------------------------
# 3. ERA real por partido (boxscore) — solo MLB
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# 2.5 Forma reciente y descanso REALES (mismo cálculo que usa el
#     entrenamiento en generate_historical_dataset_from_espn, para que un
#     partido en vivo se sirva con la MISMA definición de "forma"/"descanso"
#     con la que el modelo aprendió, en vez de ruido aleatorio)
# ---------------------------------------------------------------------------

def get_real_form_and_rest(league: str, as_of_date: date, lookback_days: Optional[int] = None) -> Dict[str, Dict]:
    """
    Racha de los últimos 10 resultados (form, 0-1) y días de descanso
    (rest, 0-3) REALES de cada equipo, calculados con exactamente la misma
    lógica que generate_historical_dataset_from_espn() usa para entrenar
    (ver last_played/recent_results ahí) -- antes, el partido de HOY se
    servía con estos dos valores 100% aleatorios (ver _enrich_fixture_with_
    profiles en data_generator.py), aunque el modelo sí había aprendido con
    la versión real. Esto cierra ese desajuste train/serve.

    as_of_date: se usan solo partidos con fecha ANTERIOR a esta -- nunca el
        propio partido que se está por predecir (sin fuga de información).
        No puede haber partidos "completed" después de hoy, así que el
        fetch en sí se acota a min(as_of_date, hoy) -- con eso, cuando
        as_of_date es "mañana" (el caso normal al armar los partidos del
        día), esta ventana queda idéntica a la que usa
        generate_team_profiles_from_espn() y ambas reusan el mismo cache
        (ver fetch_completed_games_cached) en vez de pedirle a ESPN dos
        veces el mismo histórico en un mismo request.
    """
    if lookback_days is None:
        lookback_days = LEAGUE_LOOKBACK_DAYS.get(league, DEFAULT_LOOKBACK_DAYS)

    fetch_end = min(as_of_date, date.today())
    start = fetch_end - timedelta(days=lookback_days)
    games = fetch_completed_games_cached(league, start, fetch_end)
    if not games:
        return {}

    df = pd.DataFrame(games)
    df["date"] = pd.to_datetime(df["date"])
    as_of_ts = pd.Timestamp(as_of_date)
    df = df[df["date"] < as_of_ts].sort_values("date")

    last_played: Dict[str, pd.Timestamp] = {}
    recent_results: Dict[str, List[int]] = {}

    for _, g in df.iterrows():
        home, away = g["home_team"], g["away_team"]
        home_win = 1 if g["home_score"] > g["away_score"] else 0
        last_played[home] = g["date"]
        last_played[away] = g["date"]
        recent_results.setdefault(home, []).append(home_win)
        recent_results.setdefault(away, []).append(1 - home_win)
        recent_results[home] = recent_results[home][-10:]
        recent_results[away] = recent_results[away][-10:]

    result = {}
    for team in last_played:
        rest = max(0, min(3, (as_of_ts - last_played[team]).days - 1))
        form = float(np.mean(recent_results.get(team, [0.5])))
        result[team] = {
            "rest": rest,
            "form": round(form, 2),
            "games_sampled": len(recent_results.get(team, [])),
        }
    return result


def fetch_boxscore_starters(event_id: str, client: httpx.Client) -> Dict[str, Dict]:
    """
    Devuelve el abridor de cada equipo en un partido de MLB ya jugado, con
    sus stats DE ESE partido: { "home": {"pitcher_id":.., "earned_runs":.., "innings_pitched":..}, "away": {...} }
    """
    try:
        resp = client.get(MLB_SUMMARY_URL, params={"event": event_id})
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.warning(f"No se pudo obtener boxscore de {event_id}: {e}")
        return {}

    result = {}
    try:
        for team_block in data.get("boxscore", {}).get("players", []):
            home_away = team_block.get("homeAway")
            pitching_stats = next(
                (sg for sg in team_block.get("statistics", []) if sg.get("name", "").lower() == "pitching"),
                None
            )
            if not pitching_stats:
                continue

            labels = pitching_stats.get("labels", [])
            try:
                ip_idx = labels.index("IP")
                er_idx = labels.index("ER")
            except ValueError:
                continue

            best_pitcher, best_ip = None, -1.0
            for athlete_entry in pitching_stats.get("athletes", []):
                stats = athlete_entry.get("stats", [])
                if len(stats) <= max(ip_idx, er_idx):
                    continue
                try:
                    ip_val = float(str(stats[ip_idx]).replace(",", "."))
                    er_val = float(stats[er_idx])
                except (ValueError, TypeError):
                    continue

                athlete = athlete_entry.get("athlete", {})
                pid = athlete.get("id", athlete.get("displayName", "unknown"))

                if athlete_entry.get("starter", False):
                    best_pitcher = {"pitcher_id": pid, "earned_runs": er_val, "innings_pitched": ip_val}
                    break

                if ip_val > best_ip:
                    best_ip = ip_val
                    best_pitcher = {"pitcher_id": pid, "earned_runs": er_val, "innings_pitched": ip_val}

            if best_pitcher:
                result[home_away] = best_pitcher
    except Exception as e:
        logger.warning(f"Error parseando boxscore pitching de {event_id}: {e}")

    return result


def _cumulative_era(cum_er: float, cum_ip: float, default: float = 4.20) -> float:
    """ERA acumulado hasta el momento. Usa un default de liga si no hay historial."""
    if cum_ip <= 0:
        return default
    return round((cum_er * 9.0) / cum_ip, 2)


# ---------------------------------------------------------------------------
# 4. Dataset de entrenamiento real, con ERA acumulado sin leakage
# ---------------------------------------------------------------------------

def generate_historical_dataset_from_espn(
    league: str,
    lookback_days: Optional[int] = None,
    include_pitcher_era: bool = True,
    max_games_for_era: Optional[int] = 400,
) -> pd.DataFrame:
    """
    Construye un DataFrame con el mismo esquema que generate_historical_dataset(),
    con resultados reales y (para MLB) ERA real acumulado del abridor.

    lookback_days: si no se especifica, usa LEAGUE_LOOKBACK_DAYS[league] (o
        DEFAULT_LOOKBACK_DAYS si la liga no tiene un valor propio). Ligas con
        offseason larga (NFL) necesitan una ventana más amplia para no
        quedarse sin partidos reales cuando se consulta en pretemporada.
    max_games_for_era: límite de partidos a los que se les busca boxscore
        (cada uno es un request HTTP adicional). None = sin límite (lento).
        Si se trunca, los partidos más antiguos del rango se saltan el ERA
        real y usan el default de liga.
    """
    if lookback_days is None:
        lookback_days = LEAGUE_LOOKBACK_DAYS.get(league, DEFAULT_LOOKBACK_DAYS)

    end = date.today()
    start = end - timedelta(days=lookback_days)
    games = fetch_completed_games_cached(league, start, end)

    if len(games) < 30:
        logger.warning(f"Solo {len(games)} partidos reales para {league} — insuficiente")
        return pd.DataFrame()

    profiles = generate_team_profiles_from_espn(league, lookback_days=lookback_days)
    if not profiles:
        return pd.DataFrame()

    df = pd.DataFrame(games)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    fetch_era = include_pitcher_era and league == "MLB"
    era_lookup: Dict[str, Dict[str, Dict]] = {}
    if fetch_era:
        games_to_fetch = df if max_games_for_era is None else df.tail(max_games_for_era)
        if max_games_for_era is not None and len(df) > max_games_for_era:
            logger.warning(f"Limitando boxscores de ERA a los últimos {max_games_for_era} "
                            f"de {len(df)} partidos por costo de requests")
        with httpx.Client(timeout=15.0, verify=False) as client:
            for _, g in games_to_fetch.iterrows():
                starters = fetch_boxscore_starters(g["event_id"], client)
                if starters:
                    era_lookup[g["event_id"]] = starters
                time.sleep(0.05)  # cortesía con la API pública de ESPN

    # --- Córners reales de ESPN (boxscore por partido) — solo ligas de fútbol ---
    fetch_corners = league in SOCCER_LEAGUE_SLUGS
    corners_lookup: Dict[str, Tuple[float, float]] = {}
    if fetch_corners:
        league_slug = SOCCER_LEAGUE_SLUGS[league]
        games_to_fetch_corners = df if max_games_for_era is None else df.tail(max_games_for_era)
        if max_games_for_era is not None and len(df) > max_games_for_era:
            logger.warning(f"Limitando boxscores de córners a los últimos {max_games_for_era} "
                            f"de {len(df)} partidos por costo de requests")
        with httpx.Client(timeout=15.0, verify=False) as client:
            for _, g in games_to_fetch_corners.iterrows():
                result = fetch_match_corners(g["event_id"], league_slug, client)
                if result:
                    corners_lookup[g["event_id"]] = result
                time.sleep(0.05)  # cortesía con la API pública de ESPN
        logger.info(f"Córners reales de ESPN obtenidos para {len(corners_lookup)}/"
                    f"{len(games_to_fetch_corners)} partidos de {league}")

    last_played: Dict[str, pd.Timestamp] = {}
    recent_results: Dict[str, List[int]] = {}
    pitcher_cum: Dict[str, Dict[str, float]] = {}  # pitcher_id -> {"er":.., "ip":..}

    rows = []
    for _, g in df.iterrows():
        home, away = g["home_team"], g["away_team"]
        game_date = g["date"]
        home_score, away_score = g["home_score"], g["away_score"]

        h_prof = profiles.get(home)
        a_prof = profiles.get(away)
        if not h_prof or not a_prof:
            continue

        home_rest = max(0, min(3, (game_date - last_played[home]).days - 1)) if home in last_played else 2
        away_rest = max(0, min(3, (game_date - last_played[away]).days - 1)) if away in last_played else 2

        home_form = float(np.mean(recent_results.get(home, [0.5])))
        away_form = float(np.mean(recent_results.get(away, [0.5])))

        # --- ERA acumulado del abridor, ANTES de este partido (sin leakage) ---
        h_era, a_era = 4.20, 4.20
        starters = era_lookup.get(g["event_id"], {}) if fetch_era else {}
        home_starter = starters.get("home")
        away_starter = starters.get("away")

        if home_starter:
            pid = home_starter["pitcher_id"]
            cum = pitcher_cum.get(pid, {"er": 0.0, "ip": 0.0})
            h_era = _cumulative_era(cum["er"], cum["ip"])
        if away_starter:
            pid = away_starter["pitcher_id"]
            cum = pitcher_cum.get(pid, {"er": 0.0, "ip": 0.0})
            a_era = _cumulative_era(cum["er"], cum["ip"])

        margin = home_score - away_score
        total_points = home_score + away_score
        home_win = 1 if margin > 0 else 0

        # Antes esta fórmula era 100% escala baloncesto (sb_total llegaba a
        # ~125 para partidos de fútbol) — ahora usa la misma función
        # compartida que el resto del pipeline, calibrada por deporte.
        bias = estimate_matchup_bias(league, h_prof, a_prof, home_form, away_form, home_rest, away_rest)
        expected_margin = bias["expected_margin"]
        implied_home_prob = 1 / (1 + np.exp(-expected_margin / margin_prob_scale(league)))
        sb_home_odds = round(1.0 / implied_home_prob if implied_home_prob > 0.05 else 15.0, 2)
        sb_away_odds = round(1.0 / (1 - implied_home_prob) if implied_home_prob < 0.95 else 15.0, 2)
        sb_spread = round(-expected_margin * 0.9, 1)
        sb_total = round(bias["expected_total"], 1)

        # --- Córners reales del partido (si ESPN los publicó) ---
        total_corners = None
        sb_corners_total = None
        if fetch_corners:
            corners_pair = corners_lookup.get(g["event_id"])
            if corners_pair:
                total_corners = float(corners_pair[0] + corners_pair[1])
            # Línea estimada (no hay casa de apuestas real de fondo, es proxy)
            sb_corners_total = round(10.0 + (h_prof["off_rating"] + a_prof["off_rating"] - 200) * 0.03, 1)

        rows.append({
            "league": league,
            "home_team": home,
            "away_team": away,
            "home_off_rating": h_prof["off_rating"],
            "away_off_rating": a_prof["off_rating"],
            "home_def_rating": h_prof["def_rating"],
            "away_def_rating": a_prof["def_rating"],
            "home_adv": h_prof["home_adv"],
            "home_rest": home_rest,
            "away_rest": away_rest,
            "home_form": round(home_form, 2),
            "away_form": round(away_form, 2),
            "h_pitcher_era": h_era,
            "a_pitcher_era": a_era,
            "pace": h_prof["pace"],
            "home_win": home_win,
            "margin": round(margin, 2),
            "total_points": round(total_points, 2),
            "total_corners": total_corners,
            "sb_home_odds": sb_home_odds,
            "sb_away_odds": sb_away_odds,
            "sb_spread": sb_spread,
            "sb_total": sb_total,
            "sb_corners_total": sb_corners_total,
        })

        last_played[home] = game_date
        last_played[away] = game_date
        recent_results.setdefault(home, []).append(home_win)
        recent_results.setdefault(away, []).append(1 - home_win)
        recent_results[home] = recent_results[home][-10:]
        recent_results[away] = recent_results[away][-10:]

        if home_starter:
            pid = home_starter["pitcher_id"]
            cum = pitcher_cum.setdefault(pid, {"er": 0.0, "ip": 0.0})
            cum["er"] += home_starter["earned_runs"]
            cum["ip"] += home_starter["innings_pitched"]
        if away_starter:
            pid = away_starter["pitcher_id"]
            cum = pitcher_cum.setdefault(pid, {"er": 0.0, "ip": 0.0})
            cum["er"] += away_starter["earned_runs"]
            cum["ip"] += away_starter["innings_pitched"]

    result_df = pd.DataFrame(rows)
    logger.info(f"Dataset histórico real ESPN para {league}: {len(result_df)} partidos "
                f"(ERA real: {'sí' if fetch_era else 'no'})")
    return result_df
