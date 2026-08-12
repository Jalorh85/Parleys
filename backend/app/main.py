import os
import json
import logging
import joblib
import numpy as np
import pandas as pd
from datetime import date, datetime, timedelta, timezone
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("parleys_ai")

from app.ml.data_generator import (
    LEAGUE_TEAMS,
    get_team_profiles_with_real_fallback,
    get_2026_upcoming_fixtures,
    get_upcoming_fixtures,
    generate_historical_dataset,
    blend_real_and_synthetic,
)
from app.ml.feature_engineering import dict_to_features, extract_features
from app.ml.ensemble_model import MetaEnsembleSportsModel
from app.ml.backtester import run_backtest
from app.ml.espn_historical import (
    generate_historical_dataset_from_espn,
)
from app.ml.prediction_log import (
    log_predictions,
    reconcile_league,
    get_accuracy_summary,
    get_bankroll_simulation,
)

app = FastAPI(
    title="PARLEYS AI - Sports Prediction & Machine Learning Engine (2026)",
    description="APIs for NFL, MLB, WNBA, KBO, MX & LCUP predictions using SVM, Neural Networks, Random Forest, XGBoost & LightGBM",
    version="1.0.0"
)

# Enable CORS for frontend dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_scheduler = BackgroundScheduler(timezone="UTC")


@app.on_event("startup")
def _on_startup():
    # Si el modelo de una liga no existe o está vencido (más viejo que
    # RETRAIN_INTERVAL_HOURS), lo entrenamos una vez al arrancar. Si ya
    # existe y está vigente (Volume persistente de Railway), NO se toca --
    # así un deploy normal no le cambia la predicción a nadie.
    for league in ALL_LEAGUES:
        if _model_is_stale(league):
            try:
                _train_league_model(league, n_samples=1200)
            except Exception as e:
                logger.error(f"No se pudo entrenar {league} al arrancar: {e}")
        else:
            try:
                get_or_load_model(league)
            except Exception as e:
                logger.error(f"No se pudo cargar el modelo persistido de {league}: {e}")

    # Reconciliar predicciones pendientes una vez al arrancar -- red de
    # seguridad: si el server estuvo caído, esto resuelve lo pendiente de
    # inmediato en vez de esperar al próximo ciclo de las RETRAIN_HOUR_UTC.
    for league in ALL_LEAGUES:
        try:
            reconcile_league(league)
        except Exception as e:
            logger.warning(f"No se pudo reconciliar predicciones de {league} al arrancar: {e}")

    # Reconciliación diaria (revisa predicciones vs resultado real de ESPN)
    # ANTES del retrain, a la misma hora fija -- así el log de precisión
    # queda al día justo cuando también se actualiza el modelo.
    _scheduler.add_job(
        reconcile_all_leagues_job,
        CronTrigger(hour=RETRAIN_HOUR_UTC, minute=0, timezone="UTC"),
        id="reconcile_all_leagues",
        replace_existing=True,
    )

    # Retrain recurrente, desacoplado de deploys y de tráfico. Hora FIJA
    # (no un intervalo rodante desde que arrancó el proceso) -- así,
    # pase lo que pase con el uptime/redeploys, siempre corre a la misma
    # hora UTC, elegida para caer después de que prácticamente todos los
    # partidos del día anterior de tus ligas (incluida MLB costa oeste,
    # que puede terminar pasada la 1am hora Pacífico ~08-09h UTC) ya estén
    # marcados como "completed" en ESPN y por lo tanto entren en el próximo
    # dataset de entrenamiento. 15 minutos después de la reconciliación
    # para no pegarle a ESPN con las dos cosas al mismo tiempo.
    _scheduler.add_job(
        retrain_all_leagues_job,
        CronTrigger(hour=RETRAIN_HOUR_UTC, minute=15, timezone="UTC"),
        id="retrain_all_leagues",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info(
        f"Scheduler iniciado: reconciliación a las {RETRAIN_HOUR_UTC:02d}:00 UTC, "
        f"retrain a las {RETRAIN_HOUR_UTC:02d}:15 UTC, todos los días."
    )


@app.on_event("shutdown")
def _on_shutdown():
    _scheduler.shutdown(wait=False)

# En Railway, MODEL_DIR debe apuntar al mount path de un Volume persistente
# (ej. "/data/models"), configurado por variable de entorno. Si no está
# seteada, cae al directorio local del contenedor (se pierde en cada
# deploy — solo pensado para desarrollo local).
MODEL_DIR = os.environ.get("MODEL_DIR", os.path.join(os.path.dirname(__file__), "data", "models"))
MODELS_CACHE: Dict[str, MetaEnsembleSportsModel] = {}

# Hora FIJA (UTC) a la que corre el reentrenamiento diario todos los días
# (ver CronTrigger en _on_startup). 9 UTC = 4am hora Ciudad de México / 1am
# hora Pacífico -- cae después de que hasta los partidos nocturnos de la
# costa oeste de MLB ya terminaron y ESPN los marcó "completed". Si tus
# ligas más relevantes terminan más tarde, subí este número.
RETRAIN_HOUR_UTC = int(os.environ.get("RETRAIN_HOUR_UTC", "9"))

# Ya NO define la cadencia del reentrenamiento diario (eso lo fija
# RETRAIN_HOUR_UTC arriba, a hora fija). Ahora solo se usa como red de
# seguridad al arrancar: si el último modelo persistido tiene más de estas
# horas (ej. el server estuvo caído varios días), se re-entrena una vez de
# inmediato en vez de esperar al próximo ciclo de las RETRAIN_HOUR_UTC.
RETRAIN_INTERVAL_HOURS = float(os.environ.get("RETRAIN_INTERVAL_HOURS", "24"))

# Qué tanto peso le da la predicción final a la probabilidad implícita del
# mercado (cuota REAL, ver odds_api.py) frente a la del ensemble propio.
# 0.35 = 65% modelo / 35% mercado. Solo aplica cuando hay cuota real
# (odds_source == "real"); con cuota estimada nunca se mezcla (ver
# ensemble_model.py:predict_one -- sería circular). Subir este valor hace
# la predicción más parecida al mercado (menos oportunidades de +EV, pero
# más creíbles); bajarlo la acerca más al modelo puro.
MARKET_BLEND_WEIGHT = float(os.environ.get("MARKET_BLEND_WEIGHT", "0.35"))
ALL_LEAGUES = ["LCUP", "MLB", "WNBA", "KBO", "MX", "NFL"]


def _meta_path(league: str) -> str:
    return os.path.join(MODEL_DIR, f"model_{league}.meta.json")


def _read_meta(league: str) -> Optional[Dict]:
    path = _meta_path(league)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return None


def _write_meta(league: str, n_real_games: int, source: str) -> None:
    try:
        os.makedirs(MODEL_DIR, exist_ok=True)
        with open(_meta_path(league), "w") as f:
            json.dump({
                "league": league,
                "trained_at": datetime.now(timezone.utc).isoformat(),
                "n_real_games": n_real_games,
                "data_source": source,
            }, f)
    except Exception as e:
        logger.info(f"No se pudo escribir metadata de {league}: {e}")


def _get_real_kbo_profiles() -> Dict[str, Dict]:
    """KBO no está en ESPN -> su versión "real" de perfiles de equipo viene
    de la tabla de posiciones de TheSportsDB en su lugar (ver kbo_thesportsdb.py).
    Devuelve {} si no está disponible, para que el llamador caiga al sintético."""
    try:
        from app.ml.kbo_thesportsdb import get_real_kbo_team_profiles
        return get_real_kbo_team_profiles()
    except Exception as e:
        logger.warning(f"No se pudieron obtener perfiles reales de KBO (TheSportsDB): {e}")
        return {}


def get_historical_dataset(league: str, n_samples: int = 1000) -> pd.DataFrame:
    """
    Punto único de acceso al dataset histórico. Combina datos reales de ESPN
    (últimos resultados, forma reciente, localía) con datos sintéticos de
    relleno mediante una rampa continua (blend_real_and_synthetic) en vez de
    un salto todo-o-nada al cruzar cierta cantidad de partidos reales. KBO no
    está en ESPN, así que en su lugar usa perfiles reales de TheSportsDB
    (standings) para sesgar el dataset sintético con datos reales de fuerza
    de equipo.
    """
    df_real = generate_historical_dataset_from_espn(league)
    kbo_profiles = _get_real_kbo_profiles() if league == "KBO" else None
    df_hist = blend_real_and_synthetic(league, df_real, n_samples=n_samples, extra_profiles=kbo_profiles)
    return df_hist


def get_historical_dataset_with_meta(league: str, n_samples: int = 1000):
    """Igual que get_historical_dataset(), pero además devuelve cuántos
    partidos reales de ESPN se usaron -- solo lo necesita el job de
    retrain programado, para dejarlo registrado en el .meta.json."""
    df_real = generate_historical_dataset_from_espn(league)
    kbo_profiles = _get_real_kbo_profiles() if league == "KBO" else None
    df_hist = blend_real_and_synthetic(league, df_real, n_samples=n_samples, extra_profiles=kbo_profiles)
    return df_hist, len(df_real)


def get_team_profiles(league: str) -> Dict[str, Dict]:
    """Perfiles de equipo: reales de ESPN si hay datos; para KBO (que no está
    en ESPN), reales de TheSportsDB; si no, sintéticos. Delega en la función
    centralizada de data_generator.py -- get_upcoming_fixtures() usa la
    misma, así /api/predict, /api/leagues y los partidos reales del
    dashboard quedan consistentes entre sí."""
    return get_team_profiles_with_real_fallback(league)


def get_or_load_model(league: str) -> MetaEnsembleSportsModel:
    """
    IMPORTANTE: esta función solo CARGA modelos, no los reentrena en el
    camino de una request (salvo la primera vez que Railway arranca con un
    Volume vacío, ej. la primerísima vez que se despliega el proyecto).
    El reentrenamiento normal ocurre en un job programado en background
    (ver retrain_all_leagues_job), desacoplado de deploys y de requests, así
    que una predicción no cambia solo porque hiciste `git push`.
    """
    if league in MODELS_CACHE:
        return MODELS_CACHE[league]

    model_path = os.path.join(MODEL_DIR, f"model_{league}.joblib")
    if os.path.exists(model_path):
        try:
            model = joblib.load(model_path)
            # Sanity check: verificar compatibilidad del esquema
            model.predict_one(dict_to_features({}))
            MODELS_CACHE[league] = model
            return model
        except Exception as e:
            logger.warning(
                f"Modelo cacheado para {league} incompatible ({e!r}). Se re-entrenará."
            )
            try:
                os.remove(model_path)
            except Exception:
                pass

    # Solo llegamos acá si el Volume está vacío (primer arranque del
    # proyecto en Railway) o el modelo guardado estaba corrupto. Entrenamos
    # una vez, ya con datos reales+sintéticos mezclados (no la versión
    # "ultrarrápida" de 80 muestras de antes), y lo persistimos para que la
    # próxima request y el próximo deploy lo reutilicen sin reentrenar.
    try:
        model = _train_league_model(league, n_samples=1200)
        return model
    except Exception as e:
        logger.error(f"Error entrenando modelo fallback para {league}: {e}")
        model = MetaEnsembleSportsModel()
        MODELS_CACHE[league] = model
        return model


def _train_league_model(league: str, n_samples: int = 1200) -> MetaEnsembleSportsModel:
    """Entrena, persiste (joblib + metadata) y cachea en memoria el modelo
    de una liga. Usa siempre la mezcla real+sintética (últimos resultados,
    localía, forma reciente) vía get_historical_dataset_with_meta."""
    df_hist, n_real_games = get_historical_dataset_with_meta(league, n_samples=n_samples)
    X = extract_features(df_hist)
    y_corners = df_hist["total_corners"] if "total_corners" in df_hist.columns else None

    model = MetaEnsembleSportsModel()
    model.fit(X, df_hist["home_win"], df_hist["margin"], df_hist["total_points"], y_corners=y_corners)

    model_path = os.path.join(MODEL_DIR, f"model_{league}.joblib")
    try:
        os.makedirs(MODEL_DIR, exist_ok=True)
        joblib.dump(model, model_path)
        source = "espn_real" if n_real_games >= 30 else ("blend" if n_real_games >= 8 else "sintetico")
        _write_meta(league, n_real_games=n_real_games, source=source)
        logger.info(f"{league}: modelo entrenado y guardado ({n_real_games} partidos reales, fuente={source})")
    except Exception as e:
        logger.info(f"No se pudo guardar el modelo de {league} en disco: {e}")

    MODELS_CACHE[league] = model
    return model


def reconcile_all_leagues_job() -> None:
    """Job programado (APScheduler) que revisa las predicciones ya
    registradas (ver prediction_log.log_predictions, llamado desde
    /api/fixtures) contra los resultados REALES de ESPN y marca cada una
    como acierto/fallo de ganador y de Over/Under. Corre todos los días,
    justo antes del retrain, para que /api/accuracy siempre refleje los
    partidos de ayer."""
    logger.info("Iniciando reconciliación de predicciones de todas las ligas...")
    for league in ALL_LEAGUES:
        try:
            result = reconcile_league(league)
            logger.info(f"Reconciliación {league}: {result}")
        except Exception as e:
            logger.error(f"Reconciliación programada falló para {league}: {e}")
    logger.info("Reconciliación de predicciones completada.")


def retrain_all_leagues_job() -> None:
    """Job programado (APScheduler) que reentrena y persiste el modelo de
    cada liga usando los últimos resultados reales disponibles. Corre solo,
    sin depender de deploys ni de que llegue tráfico -- así el modelo se
    actualiza todos los días a la hora fija que vos definís (RETRAIN_HOUR_UTC)
    y no con la cadencia de tus `git push`."""
    logger.info("Iniciando retrain programado de todas las ligas...")
    for league in ALL_LEAGUES:
        try:
            _train_league_model(league, n_samples=1200)
        except Exception as e:
            logger.error(f"Retrain programado falló para {league}: {e}")
    logger.info("Retrain programado completado.")


def _model_is_stale(league: str) -> bool:
    meta = _read_meta(league)
    if not meta:
        return True
    try:
        trained_at = datetime.fromisoformat(meta["trained_at"])
        age_hours = (datetime.now(timezone.utc) - trained_at).total_seconds() / 3600.0
        return age_hours >= RETRAIN_INTERVAL_HOURS
    except Exception:
        return True


class MatchupPredictRequest(BaseModel):
    league: str
    home_team: str
    away_team: str
    home_rest: int = 1
    away_rest: int = 1
    home_form: float = 0.55
    away_form: float = 0.50
    h_pitcher_era: float = 3.80
    a_pitcher_era: float = 3.95
    sb_home_odds: float = 1.90
    sb_away_odds: float = 1.90
    sb_spread: float = -3.5
    sb_total: float = 210.5
    sb_corners_total: Optional[float] = None  # solo aplica a Liga MX

class BacktestRequest(BaseModel):
    league: str = "LCUP"
    initial_bankroll: float = 1000.0
    staking_strategy: str = "kelly"
    flat_stake_pct: float = 0.03
    min_ev_pct: float = 2.0
    min_confidence: float = 10.0

class RetrainRequest(BaseModel):
    league: str = "LCUP"
    svm_c: float = 1.0
    svm_kernel: str = "rbf"
    nn_learning_rate: float = 0.001
    nn_hidden_size: int = 64
    xgb_n_estimators: int = 150
    xgb_max_depth: int = 4
    lgbm_n_estimators: int = 150
    lgbm_max_depth: int = 5

class ParlayLeg(BaseModel):
    fixture_id: str
    league: str
    home_team: str
    away_team: str
    pick: str # "HOME", "AWAY", "OVER", "UNDER"
    odds: float
    prob: float

class ParlayRequest(BaseModel):
    legs: List[ParlayLeg]
    stake: float = 50.0

@app.get("/")
def root():
    return {
        "status": "online",
        "system": "PARLEYS AI Prediction Engine 2026",
        "leagues_supported": ["LCUP", "MLB", "WNBA", "KBO", "MX", "NFL"],
        "models": ["Support Vector Machines (SVM)", "Neural Networks (MLP)", "Random Forest", "XGBoost", "LightGBM", "Meta-Ensemble"]
    }

@app.get("/api/leagues")
def get_leagues():
    response = {}
    for league, teams in LEAGUE_TEAMS.items():
        profiles = get_team_profiles(league)
        response[league] = {
            "teams": teams,
            "team_profiles": profiles
        }
    return response

@app.get("/api/fixtures")
def get_fixtures(
    league: str = Query("LCUP"),
    date: Optional[str] = Query(None, description="Fecha en formato YYYY-MM-DD. Por defecto: mañana.")
):
    if league not in LEAGUE_TEAMS:
        raise HTTPException(status_code=400, detail="Liga no válida")

    # Parsear la fecha o usar mañana por defecto
    if date:
        try:
            from datetime import datetime
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de fecha inválido. Usa YYYY-MM-DD")
    else:
        from datetime import date as date_type
        target_date = date_type.today() + timedelta(days=1)

    try:
        raw_fixtures = get_upcoming_fixtures(league, target_date=target_date)
    except Exception as e:
        return {
            "league": league,
            "date": target_date.strftime("%Y-%m-%d"),
            "count": 0,
            "fixtures": [],
            "error": str(e)
        }

    # Sin partidos reales para esta fecha/liga -> ya no se rellena con
    # partidos simulados (ver get_upcoming_fixtures). Se corta acá antes de
    # cargar/entrenar el modelo (evita trabajo innecesario) y se devuelve un
    # mensaje claro para que el frontend lo muestre en vez de una lista vacía muda.
    if not raw_fixtures:
        return {
            "league": league,
            "date": target_date.strftime("%Y-%m-%d"),
            "count": 0,
            "fixtures": [],
            "message": (
                f"No hay partidos reales para la fecha del "
                f"{target_date.strftime('%d/%m/%Y')}. Revisa el calendario "
                f"para consultar los partidos en otra fecha."
            )
        }

    try:
        model = get_or_load_model(league)
    except Exception as e:
        return {
            "league": league,
            "date": target_date.strftime("%Y-%m-%d"),
            "count": len(raw_fixtures),
            "fixtures": raw_fixtures,
            "error": f"Modelo no disponible: {str(e)}"
        }

    enhanced_fixtures = []
    for fix in raw_fixtures:
        try:
            X = dict_to_features(fix)
            prediction = model.predict_one(
                X,
                sb_home_odds=fix["sb_home_odds"],
                sb_away_odds=fix["sb_away_odds"],
                sb_spread=fix["sb_spread"],
                sb_total=fix["sb_total"],
                sb_corners_total=fix.get("sb_corners_total"),
                league=league,
                odds_are_real=(fix.get("odds_source") == "real"),
                market_blend_weight=MARKET_BLEND_WEIGHT,
            )
            fix["prediction"] = prediction
        except Exception as e:
            logger.exception(f"Error prediciendo fixture {fix.get('fixture_id')} ({league})")
            fix["prediction"] = None
            fix["prediction_error"] = str(e)
        enhanced_fixtures.append(fix)

    # Best-effort: si falla el log de predicciones, no debe tumbar la
    # respuesta del dashboard -- ver prediction_log.py.
    try:
        log_predictions(league, enhanced_fixtures)
    except Exception as e:
        logger.warning(f"No se pudo registrar el log de predicciones de {league}: {e}")

    return {
        "league": league,
        "date": target_date.strftime("%Y-%m-%d"),
        "count": len(enhanced_fixtures),
        "fixtures": enhanced_fixtures
    }


@app.post("/api/predict")
def predict_matchup(req: MatchupPredictRequest):
    if req.league not in LEAGUE_TEAMS:
        raise HTTPException(status_code=400, detail="Liga no válida")

    model = get_or_load_model(req.league)
    profiles = get_team_profiles(req.league)

    h_prof = profiles.get(req.home_team, {"off_rating": 100, "def_rating": 100, "home_adv": 3.0, "pace": 100})
    a_prof = profiles.get(req.away_team, {"off_rating": 100, "def_rating": 100, "home_adv": 0.0, "pace": 100})

    input_data = {
        "home_off_rating": h_prof["off_rating"],
        "away_off_rating": a_prof["off_rating"],
        "home_def_rating": h_prof["def_rating"],
        "away_def_rating": a_prof["def_rating"],
        "home_adv": h_prof["home_adv"],
        "home_rest": req.home_rest,
        "away_rest": req.away_rest,
        "home_form": req.home_form,
        "away_form": req.away_form,
        "h_pitcher_era": req.h_pitcher_era,
        "a_pitcher_era": req.a_pitcher_era,
        "pace": h_prof["pace"]
    }

    X = dict_to_features(input_data)
    result = model.predict_one(
        X,
        sb_home_odds=req.sb_home_odds,
        sb_away_odds=req.sb_away_odds,
        sb_spread=req.sb_spread,
        sb_total=req.sb_total,
        sb_corners_total=req.sb_corners_total,
        league=req.league
    )

    return {
        "request": req.dict(),
        "input_features": input_data,
        "prediction": result
    }

@app.get("/api/metrics")
def get_model_metrics(league: str = Query("LCUP")):
    df_hist = get_historical_dataset(league, n_samples=600)
    X = extract_features(df_hist)
    model = get_or_load_model(league)

    svm_preds = [model.svm.predict_one(X.iloc[[i]]) for i in range(len(X))]
    nn_preds = [model.nn.predict_one(X.iloc[[i]]) for i in range(len(X))]
    xgb_preds = [model.xgb.predict_one(X.iloc[[i]]) for i in range(len(X))]
    lgbm_preds = [model.lgbm.predict_one(X.iloc[[i]]) for i in range(len(X))]
    ens_preds = [
        model.predict_one(
            X.iloc[[i]],
            sb_home_odds=df_hist.iloc[i]["sb_home_odds"],
            sb_away_odds=df_hist.iloc[i]["sb_away_odds"],
            sb_spread=df_hist.iloc[i]["sb_spread"],
            sb_total=df_hist.iloc[i]["sb_total"],
            sb_corners_total=df_hist.iloc[i].get("sb_corners_total"),
            league=league
        )
        for i in range(len(X))
    ]

    y_win = df_hist["home_win"]
    y_total = df_hist["total_points"]

    def _win_acc(preds):
        return round(float(np.mean([1 if p["predicted_winner"] == ("HOME" if y_win.iloc[i] == 1 else "AWAY") else 0 for i, p in enumerate(preds)])) * 100, 2)

    def _total_mae(preds, key="predicted_total"):
        return round(float(np.mean([abs(p[key] - y_total.iloc[i]) for i, p in enumerate(preds)])), 2)

    svm_acc = _win_acc(svm_preds)
    nn_acc = _win_acc(nn_preds)
    xgb_acc = _win_acc(xgb_preds)
    lgbm_acc = _win_acc(lgbm_preds)
    ens_acc = round(float(np.mean([1 if p["ensemble"]["predicted_winner"] == ("HOME" if y_win.iloc[i] == 1 else "AWAY") else 0 for i, p in enumerate(ens_preds)])) * 100, 2)

    svm_mae = _total_mae(svm_preds)
    nn_mae = _total_mae(nn_preds)
    xgb_mae = _total_mae(xgb_preds)
    lgbm_mae = _total_mae(lgbm_preds)
    ens_mae = round(float(np.mean([abs(p["ensemble"]["predicted_total"] - y_total.iloc[i]) for i, p in enumerate(ens_preds)])), 2)

    return {
        "league": league,
        "sample_size": len(X),
        "comparison": [
            {"model": "Support Vector Machine (SVM)", "win_accuracy": svm_acc, "total_mae": svm_mae, "roi_est": round(svm_acc - 52.4, 2)},
            {"model": "Redes Neuronales (MLP)", "win_accuracy": nn_acc, "total_mae": nn_mae, "roi_est": round(nn_acc - 52.4, 2)},
            {"model": "XGBoost", "win_accuracy": xgb_acc, "total_mae": xgb_mae, "roi_est": round(xgb_acc - 52.4, 2)},
            {"model": "LightGBM", "win_accuracy": lgbm_acc, "total_mae": lgbm_mae, "roi_est": round(lgbm_acc - 52.4, 2)},
            {"model": "Meta-Ensemble (SVM+NN+RF+XGB+LGBM)", "win_accuracy": ens_acc, "total_mae": ens_mae, "roi_est": round(ens_acc - 52.4, 2)}
        ]
    }

@app.get("/api/accuracy")
def get_real_accuracy(
    league: Optional[str] = Query(None, description="Si se omite, agrega todas las ligas"),
    days: int = Query(30, ge=1, le=365, description="Ventana de días hacia atrás")
):
    """
    Precisión REAL medida contra resultados reales ya reconciliados (ver
    prediction_log.py) -- NO precisión sobre datos de entrenamiento/backtest
    como /api/metrics. Esto es lo que responde "¿el reentrenamiento diario
    realmente está mejorando el modelo con el tiempo?" con datos, no con
    intuición. Los partidos de un día quedan reflejados acá recién después
    de que corre la reconciliación programada (ver reconcile_all_leagues_job),
    normalmente entre 1 y 2 días después de jugados.
    """
    if league and league not in LEAGUE_TEAMS:
        raise HTTPException(status_code=400, detail="Liga no válida")
    leagues = [league] if league else ALL_LEAGUES
    return get_accuracy_summary(leagues, days=days)


@app.post("/api/accuracy/reconcile")
def trigger_reconciliation(league: Optional[str] = Query(None)):
    """Dispara la reconciliación manualmente (sin esperar al job diario) --
    útil para probar el flujo o para forzar una actualización tras cargar
    predicciones nuevas."""
    leagues = [league] if league else ALL_LEAGUES
    if league and league not in LEAGUE_TEAMS:
        raise HTTPException(status_code=400, detail="Liga no válida")
    results = []
    for lg in leagues:
        try:
            results.append(reconcile_league(lg))
        except Exception as e:
            results.append({"league": lg, "error": str(e)})
    return {"results": results}


@app.get("/api/bankroll")
def get_bankroll(
    league: Optional[str] = Query(None, description="Si se omite, agrega todas las ligas"),
    days: int = Query(90, ge=1, le=365, description="Ventana de días hacia atrás"),
    stake: float = Query(10.0, gt=0, description="Monto simulado por apuesta"),
    only_value_bets: bool = Query(True, description="True: solo picks marcados +EV. False: siempre el ganador predicho")
):
    """
    Simulación retrospectiva de bankroll: "si hubieras apostado `stake` a
    cada pick desde hace `days` días, ¿cuánto tendrías hoy?". Usa
    EXCLUSIVAMENTE predicciones ya reconciliadas contra resultados reales
    (ver prediction_log.py) y las cuotas registradas en el momento de la
    predicción -- nunca inventa ni ajusta un resultado después del hecho.

    Esto es una simulación informativa con datos históricos, NO una
    recomendación de apuesta ni garantía de resultados futuros.
    """
    if league and league not in LEAGUE_TEAMS:
        raise HTTPException(status_code=400, detail="Liga no válida")
    leagues = [league] if league else ALL_LEAGUES
    return get_bankroll_simulation(leagues, days=days, stake=stake, only_value_bets=only_value_bets)


@app.post("/api/backtest")
def run_backtest_endpoint(req: BacktestRequest):
    model = get_or_load_model(req.league)
    df_hist = get_historical_dataset(req.league, n_samples=800)

    backtest_result = run_backtest(
        model=model,
        df=df_hist,
        initial_bankroll=req.initial_bankroll,
        staking_strategy=req.staking_strategy,
        flat_stake_pct=req.flat_stake_pct,
        min_ev_pct=req.min_ev_pct,
        min_confidence=req.min_confidence
    )

    return {
        "league": req.league,
        "parameters": req.dict(),
        "result": backtest_result
    }

@app.post("/api/parlay")
def calculate_parlay(req: ParlayRequest):
    if not req.legs:
        raise HTTPException(status_code=400, detail="Debes seleccionar al menos una selección para la combinada")

    combined_odds = 1.0
    combined_prob = 1.0

    for leg in req.legs:
        combined_odds *= leg.odds
        combined_prob *= leg.prob

    combined_odds = round(combined_odds, 2)
    combined_prob_pct = round(combined_prob * 100, 2)
    
    potential_payout = round(req.stake * combined_odds, 2)
    potential_profit = round(potential_payout - req.stake, 2)
    
    parlay_ev_pct = round(((combined_prob * combined_odds) - 1.0) * 100, 1)

    return {
        "leg_count": len(req.legs),
        "stake": req.stake,
        "combined_odds": combined_odds,
        "win_probability_pct": combined_prob_pct,
        "potential_payout": potential_payout,
        "potential_profit": potential_profit,
        "parlay_ev_pct": parlay_ev_pct,
        "recommendation": "EXCELENTE VALOR (+EV)" if parlay_ev_pct > 5.0 else ("ACEPTABLE" if parlay_ev_pct > 0 else "ALTO RIESGO / NEGATIVO EV")
    }

@app.post("/api/retrain")
def retrain_models(req: RetrainRequest):
    df_hist, n_real_games = get_historical_dataset_with_meta(req.league, n_samples=1200)
    X = extract_features(df_hist)
    y_corners = df_hist["total_corners"] if "total_corners" in df_hist.columns else None

    # Custom training (hiperparámetros del usuario vía ModelTrainerUI)
    new_model = MetaEnsembleSportsModel(svm_weight=0.15, nn_weight=0.20, rf_weight=0.15, xgb_weight=0.25, lgbm_weight=0.25)
    new_model.svm.c = req.svm_c
    new_model.svm.kernel = req.svm_kernel
    new_model.nn.learning_rate_init = req.nn_learning_rate
    new_model.nn.hidden_layer_sizes = (req.nn_hidden_size, req.nn_hidden_size // 2)

    new_model.fit(X, df_hist["home_win"], df_hist["margin"], df_hist["total_points"], y_corners=y_corners)

    # Save & Cache
    try:
        os.makedirs(MODEL_DIR, exist_ok=True)
        model_path = os.path.join(MODEL_DIR, f"model_{req.league}.joblib")
        joblib.dump(new_model, model_path)
        source = "espn_real" if n_real_games >= 30 else ("blend" if n_real_games >= 8 else "sintetico")
        _write_meta(req.league, n_real_games=n_real_games, source=source)
    except Exception as e:
        logger.info(f"No se pudo guardar el modelo en disco (Read-only filesystem): {e}")
    MODELS_CACHE[req.league] = new_model

    return {
        "message": f"Modelo para {req.league} re-entrenado exitosamente",
        "parameters": req.dict(),
        "n_real_games_used": n_real_games,
        "status": "ready"
    }


@app.get("/api/model-status")
def model_status():
    """Transparencia: qué modelo está sirviendo cada liga ahora mismo y con
    qué datos fue entrenado -- útil para ver de un vistazo si LCUP está
    usando datos reales de ESPN, la mezcla, o todavía el fallback sintético."""
    status = {}
    for league in ALL_LEAGUES:
        meta = _read_meta(league)
        status[league] = meta or {"league": league, "trained_at": None, "n_real_games": None, "data_source": "no entrenado aún"}
    return status

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
