"""
prediction_log.py — Registra cada predicción real que ve el usuario y, un
día después, la reconcilia contra el resultado REAL del partido (ESPN),
para poder medir con datos -- no con intuición -- si el reentrenamiento
diario (ver main.py: retrain_all_leagues_job) realmente mejora la
precisión del modelo con el tiempo.

IMPORTANTE -- qué es y qué NO es esto:
  Esto NO alimenta al entrenamiento (el modelo no "ve" este log). El
  reentrenamiento diario ya aprende de los resultados reales por su cuenta,
  directo de ESPN (ver get_historical_dataset_with_meta en main.py). Este
  módulo es la capa de OBSERVABILIDAD: te dice, con números reales,
  cuántas veces acertó el ensemble ayer/la semana pasada/el mes pasado,
  para que puedas confirmar que el reentrenamiento efectivamente está
  funcionando (o detectar si empeora) en vez de asumirlo a ciegas.

Flujo:
  1. Cada vez que /api/fixtures arma predicciones reales, log_predictions()
     las guarda (upsert por fixture_id -- no duplica si el mismo partido
     se vuelve a consultar el mismo día).
  2. Un job programado (reconcile_all_leagues_job en main.py) corre todos
     los días, busca predicciones sin resolver cuyo partido ya debería
     haber terminado, las cruza contra el resultado real de ESPN
     (fetch_completed_games) por fixture_id/event_id -- son el mismo
     campo "id" de ESPN en ambos lados -- y marca acierto/fallo.
  3. get_accuracy_summary() agrega esas reconciliaciones en un resumen
     por liga y por día, listo para exponer en /api/accuracy.

Almacenamiento: un archivo JSON por liga en MODEL_DIR (el mismo Volume
persistente de Railway que ya usás para los modelos .joblib), así
sobrevive a deploys igual que ellos. Escritura atómica (archivo temporal +
os.replace) para no dejar un JSON corrupto a medias si el proceso muere
en mitad de un guardado.
"""

import os
import json
import logging
import threading
from datetime import date, datetime, timedelta, timezone
from typing import Dict, List, Optional

logger = logging.getLogger("parleys_ai")

# Mismo Volume persistente que usan los modelos (ver MODEL_DIR en main.py) --
# se lee la misma variable de entorno para que ambos coincidan siempre.
MODEL_DIR = os.environ.get(
    "MODEL_DIR", os.path.join(os.path.dirname(__file__), "..", "data", "models")
)

# Predicciones resueltas más viejas que esto se podan en cada reconciliación
# programada, para que el archivo no crezca sin límite con los años.
MAX_LOG_AGE_DAYS = 400

_locks: Dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()


def _lock_for(league: str) -> threading.Lock:
    with _locks_guard:
        if league not in _locks:
            _locks[league] = threading.Lock()
        return _locks[league]


def _log_path(league: str) -> str:
    return os.path.join(MODEL_DIR, f"predictions_{league}.json")


def _load_log(league: str) -> Dict[str, Dict]:
    path = _log_path(league)
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"No se pudo leer el log de predicciones de {league}, se reinicia vacío: {e}")
        return {}


def _save_log(league: str, log: Dict[str, Dict]) -> None:
    try:
        os.makedirs(MODEL_DIR, exist_ok=True)
        path = _log_path(league)
        tmp_path = path + ".tmp"
        with open(tmp_path, "w") as f:
            json.dump(log, f)
        os.replace(tmp_path, path)  # escritura atómica
    except Exception as e:
        logger.warning(f"No se pudo guardar el log de predicciones de {league}: {e}")


def _prune_old(log: Dict[str, Dict]) -> Dict[str, Dict]:
    cutoff = (date.today() - timedelta(days=MAX_LOG_AGE_DAYS)).strftime("%Y-%m-%d")
    return {fid: rec for fid, rec in log.items() if rec.get("date", "9999-99-99") >= cutoff}


# ---------------------------------------------------------------------
# 1. Registro de predicciones (llamado desde /api/fixtures)
# ---------------------------------------------------------------------

def log_predictions(league: str, enhanced_fixtures: List[Dict]) -> None:
    """
    Guarda (upsert por fixture_id) la predicción del ensemble para cada
    partido real de `enhanced_fixtures` (la lista que ya trae `prediction`
    calculada). No pisa registros ya reconciliados -- si alguien vuelve a
    pedir /api/fixtures para una fecha vieja cuyo resultado ya se cargó, el
    resultado real no se pierde.
    """
    if not enhanced_fixtures:
        return

    with _lock_for(league):
        log = _load_log(league)
        now_iso = datetime.now(timezone.utc).isoformat()
        changed = False

        for fix in enhanced_fixtures:
            fid = fix.get("fixture_id")
            pred = fix.get("prediction")
            if not fid or not pred or not pred.get("ensemble"):
                continue

            existing = log.get(fid)
            if existing and existing.get("resolved"):
                continue  # ya tiene resultado real -- no lo pisamos

            ens = pred["ensemble"]
            log[fid] = {
                "fixture_id": fid,
                "league": league,
                "date": fix.get("date"),
                "home_team": fix.get("home_team"),
                "away_team": fix.get("away_team"),
                "predicted_winner": ens.get("predicted_winner"),
                "home_win_prob": ens.get("home_win_prob"),
                "predicted_margin": ens.get("predicted_margin"),
                "predicted_total": ens.get("predicted_total"),
                "over_under_pick": ens.get("over_under_pick"),
                "sb_total": fix.get("sb_total"),
                "sb_home_odds": fix.get("sb_home_odds"),
                "sb_away_odds": fix.get("sb_away_odds"),
                "value_pick": ens.get("value_pick"),
                "value_ev_pct": ens.get("value_ev_pct"),
                "logged_at": (existing or {}).get("logged_at", now_iso),
                "last_updated_at": now_iso,
                "resolved": False,
            }
            changed = True

        if changed:
            _save_log(league, log)


# ---------------------------------------------------------------------
# 2. Reconciliación contra resultados reales
# ---------------------------------------------------------------------

def _fetch_completed_games_any_source(league: str, start: date, end: date) -> List[Dict]:
    """
    Resultados reales terminados, cruzables por fixture_id/event_id.
    MLB/WNBA/MX/LCUP/NFL -> ESPN (fetch_completed_games, mismo campo "id"
    que ya usa fixture_id en sports_api.py).
    KBO -> ESPN no tiene KBO, así que fetch_completed_games siempre
    devuelve []. Si en el futuro agregás a kbo_thesportsdb.py una función
    get_real_kbo_completed_games(start, end) que devuelva la MISMA forma
    ({"event_id","home_team","away_team","home_score","away_score",...}),
    se usa automáticamente acá. Hasta entonces, las predicciones de KBO se
    siguen registrando normal, solo que no se auto-resuelven.
    """
    from app.ml.espn_historical import fetch_completed_games
    games = fetch_completed_games(league, start, end)
    if games or league != "KBO":
        return games
    try:
        from app.ml.kbo_thesportsdb import get_real_kbo_completed_games
        return get_real_kbo_completed_games(start, end) or []
    except Exception:
        return []


def reconcile_league(league: str, lookback_days: int = 10) -> Dict:
    """
    Busca predicciones registradas y sin resolver de los últimos
    `lookback_days` días, las cruza contra resultados reales terminados, y
    marca acierto/fallo de ganador y de Over/Under. Devuelve un resumen de
    cuántas se revisaron y cuántas se resolvieron en esta corrida.
    """
    with _lock_for(league):
        log = _load_log(league)
        unresolved_ids = [fid for fid, rec in log.items() if not rec.get("resolved")]

        if not unresolved_ids:
            pruned = _prune_old(log)
            if len(pruned) != len(log):
                _save_log(league, pruned)
            return {"league": league, "checked": 0, "resolved_now": 0}

        end = date.today()
        start = end - timedelta(days=lookback_days)
        try:
            completed = _fetch_completed_games_any_source(league, start, end)
        except Exception as e:
            logger.warning(f"No se pudieron obtener resultados reales para reconciliar {league}: {e}")
            completed = []

        completed_by_id = {g["event_id"]: g for g in completed if g.get("event_id")}

        resolved_now = 0
        now_iso = datetime.now(timezone.utc).isoformat()
        for fid in unresolved_ids:
            g = completed_by_id.get(fid)
            if not g:
                continue

            rec = log[fid]
            home_score = g["home_score"]
            away_score = g["away_score"]

            if home_score > away_score:
                actual_winner = "HOME"
            elif away_score > home_score:
                actual_winner = "AWAY"
            else:
                actual_winner = "DRAW"  # el ensemble siempre elige HOME/AWAY -> un empate
                                         # cuenta como fallo (no puede predecir empates)

            predicted_winner = rec.get("predicted_winner")
            actual_total = home_score + away_score

            ou_pick = rec.get("over_under_pick") or ""
            sb_total = rec.get("sb_total")
            ou_correct = None
            if sb_total is not None:
                if ou_pick.startswith("OVER"):
                    ou_correct = actual_total > sb_total
                elif ou_pick.startswith("UNDER"):
                    ou_correct = actual_total < sb_total
                # "SIN VALOR (línea ajustada)" no fue una apuesta real -> queda en None

            rec["actual_home_score"] = home_score
            rec["actual_away_score"] = away_score
            rec["actual_winner"] = actual_winner
            rec["actual_total"] = actual_total
            rec["winner_correct"] = (predicted_winner == actual_winner) if predicted_winner else None
            rec["over_under_correct"] = ou_correct
            rec["resolved"] = True
            rec["resolved_at"] = now_iso
            resolved_now += 1

        log = _prune_old(log)
        if resolved_now or True:  # siempre guardamos: la poda pudo haber sacado registros viejos
            _save_log(league, log)

        return {"league": league, "checked": len(unresolved_ids), "resolved_now": resolved_now}


# ---------------------------------------------------------------------
# 3. Resumen agregado (para /api/accuracy)
# ---------------------------------------------------------------------

def get_accuracy_summary(leagues: List[str], days: int = 30) -> Dict:
    cutoff = (date.today() - timedelta(days=days)).strftime("%Y-%m-%d")

    per_league: Dict[str, Dict] = {}
    daily: Dict[str, Dict[str, int]] = {}
    total_resolved = total_correct = 0
    total_ou_resolved = total_ou_correct = 0

    for league in leagues:
        log = _load_log(league)
        resolved = [r for r in log.values() if r.get("resolved") and r.get("date", "") >= cutoff]
        correct = [r for r in resolved if r.get("winner_correct")]
        ou_resolved = [r for r in resolved if r.get("over_under_correct") is not None]
        ou_correct = [r for r in ou_resolved if r.get("over_under_correct")]

        # Desglose diario de ESTA liga -- misma forma que `daily` (el
        # agregado de todas las ligas, más abajo), para que el frontend
        # pueda dibujar una línea de tendencia por liga superpuesta
        # (ver AccuracyWidget.jsx) en vez de un solo trend combinado.
        league_daily: Dict[str, Dict[str, int]] = {}
        for r in resolved:
            d = r.get("date", "unknown")
            bucket = league_daily.setdefault(d, {"resolved": 0, "correct": 0})
            bucket["resolved"] += 1
            bucket["correct"] += 1 if r.get("winner_correct") else 0

        league_daily_sorted = [
            {
                "date": d,
                "resolved": v["resolved"],
                "correct": v["correct"],
                "accuracy_pct": round(v["correct"] / v["resolved"] * 100, 1) if v["resolved"] else None,
            }
            for d, v in sorted(league_daily.items())
        ]

        per_league[league] = {
            "resolved_predictions": len(resolved),
            "correct_winner": len(correct),
            "winner_accuracy_pct": round(len(correct) / len(resolved) * 100, 1) if resolved else None,
            "ou_resolved": len(ou_resolved),
            "ou_correct": len(ou_correct),
            "ou_accuracy_pct": round(len(ou_correct) / len(ou_resolved) * 100, 1) if ou_resolved else None,
            "daily": league_daily_sorted,
        }

        total_resolved += len(resolved)
        total_correct += len(correct)
        total_ou_resolved += len(ou_resolved)
        total_ou_correct += len(ou_correct)

        for r in resolved:
            d = r.get("date", "unknown")
            bucket = daily.setdefault(d, {"resolved": 0, "correct": 0})
            bucket["resolved"] += 1
            bucket["correct"] += 1 if r.get("winner_correct") else 0

    daily_sorted = [
        {
            "date": d,
            "resolved": v["resolved"],
            "correct": v["correct"],
            "accuracy_pct": round(v["correct"] / v["resolved"] * 100, 1) if v["resolved"] else None,
        }
        for d, v in sorted(daily.items())
    ]

    return {
        "days": days,
        "leagues": leagues,
        "overall": {
            "resolved_predictions": total_resolved,
            "correct_winner": total_correct,
            "winner_accuracy_pct": round(total_correct / total_resolved * 100, 1) if total_resolved else None,
            "ou_resolved": total_ou_resolved,
            "ou_correct": total_ou_correct,
            "ou_accuracy_pct": round(total_ou_correct / total_ou_resolved * 100, 1) if total_ou_resolved else None,
        },
        "per_league": per_league,
        "daily": daily_sorted,
    }


# ---------------------------------------------------------------------
# 4. Simulación de bankroll histórico (para /api/bankroll)
# ---------------------------------------------------------------------

def get_bankroll_simulation(leagues: List[str], days: int = 90, stake: float = 10.0,
                             only_value_bets: bool = True) -> Dict:
    """
    Simulación retrospectiva: "si hubieras apostado `stake` a cada pick
    desde hace `days` días, ¿cuánto tendrías hoy?". Usa EXCLUSIVAMENTE
    predicciones ya reconciliadas contra resultados reales (prediction_log)
    y las cuotas que estaban registradas en el momento de la predicción
    (sb_home_odds/sb_away_odds) -- nunca inventa ni ajusta un resultado
    después del hecho.

    only_value_bets=True (default): solo simula los partidos que el
        ensemble marcó como +EV (value_pick == HOME/AWAY) -- es la
        pregunta real de la app ("¿sirve seguir las señales de valor?").
    only_value_bets=False: simula apostar SIEMPRE al ganador que predijo
        el modelo, tenga o no valor marcado -- útil para comparar contra
        el caso anterior.

    Esto es una simulación informativa con datos históricos, NO una
    recomendación de apuesta ni garantía de resultados futuros.
    """
    cutoff = (date.today() - timedelta(days=days)).strftime("%Y-%m-%d")
    bets: List[Dict] = []

    for league in leagues:
        log = _load_log(league)
        for rec in log.values():
            if not rec.get("resolved") or rec.get("date", "") < cutoff:
                continue

            if only_value_bets:
                pick = rec.get("value_pick")
                if pick not in ("HOME", "AWAY"):
                    continue
            else:
                pick = rec.get("predicted_winner")
                if pick not in ("HOME", "AWAY"):
                    continue

            odds = rec.get("sb_home_odds") if pick == "HOME" else rec.get("sb_away_odds")
            if not odds or odds <= 1.0:
                continue

            won = rec.get("actual_winner") == pick
            profit = round(stake * (odds - 1.0), 2) if won else -stake

            bets.append({
                "date": rec.get("date"),
                "league": league,
                "fixture_id": rec.get("fixture_id"),
                "home_team": rec.get("home_team"),
                "away_team": rec.get("away_team"),
                "pick": pick,
                "odds": odds,
                "won": won,
                "profit": profit,
            })

    bets.sort(key=lambda b: b["date"])

    daily: Dict[str, Dict] = {}
    for b in bets:
        bucket = daily.setdefault(b["date"], {"bets": 0, "profit": 0.0})
        bucket["bets"] += 1
        bucket["profit"] += b["profit"]

    series = []
    running = 0.0
    for d in sorted(daily.keys()):
        running += daily[d]["profit"]
        series.append({
            "date": d,
            "bets": daily[d]["bets"],
            "profit": round(daily[d]["profit"], 2),
            "cumulative": round(running, 2),
        })

    total_bets = len(bets)
    total_wins = sum(1 for b in bets if b["won"])
    total_staked = round(total_bets * stake, 2)
    net_profit = round(sum(b["profit"] for b in bets), 2)

    return {
        "days": days,
        "stake_per_bet": stake,
        "only_value_bets": only_value_bets,
        "leagues": leagues,
        "total_bets": total_bets,
        "wins": total_wins,
        "losses": total_bets - total_wins,
        "win_rate_pct": round(total_wins / total_bets * 100, 1) if total_bets else None,
        "total_staked": total_staked,
        "net_profit": net_profit,
        "roi_pct": round(net_profit / total_staked * 100, 1) if total_staked else None,
        "series": series,
    }

