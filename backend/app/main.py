import os
import logging
import joblib
import numpy as np
import pandas as pd
from datetime import date, timedelta
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("parleys_ai")

from app.ml.data_generator import (
    LEAGUE_TEAMS,
    generate_team_profiles,
    get_2026_upcoming_fixtures,
    get_upcoming_fixtures,
    generate_historical_dataset,
)
from app.ml.feature_engineering import dict_to_features, extract_features
from app.ml.ensemble_model import MetaEnsembleSportsModel
from app.ml.backtester import run_backtest
from app.ml.espn_historical import (
    generate_team_profiles_from_espn,
    generate_historical_dataset_from_espn,
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

MODEL_DIR = os.path.join(os.path.dirname(__file__), "data", "models")
MODELS_CACHE: Dict[str, MetaEnsembleSportsModel] = {}


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
    Punto único de acceso al dataset histórico: intenta ESPN real primero.
    KBO no está en ESPN, así que en su lugar usa perfiles reales de
    TheSportsDB (standings) para sesgar el dataset sintético con datos
    reales de fuerza de equipo. Si nada de eso está disponible, cae al
    generador 100% sintético.
    """
    df_hist = generate_historical_dataset_from_espn(league)
    if df_hist.empty:
        kbo_profiles = _get_real_kbo_profiles() if league == "KBO" else None
        df_hist = generate_historical_dataset(league, n_samples=n_samples, profiles=kbo_profiles)
    return df_hist


def get_team_profiles(league: str) -> Dict[str, Dict]:
    """Perfiles de equipo: reales de ESPN si hay datos; para KBO (que no está
    en ESPN), reales de TheSportsDB; si no, sintéticos. Si la fuente real
    solo cubre parte de los equipos, se completa con el perfil sintético
    para que ningún equipo de LEAGUE_TEAMS quede sin perfil."""
    profiles = generate_team_profiles_from_espn(league)
    if not profiles and league == "KBO":
        profiles = _get_real_kbo_profiles()

    if not profiles:
        return generate_team_profiles(league)

    if len(profiles) < len(LEAGUE_TEAMS.get(league, [])):
        merged = generate_team_profiles(league)
        merged.update(profiles)
        return merged

    return profiles


def get_or_load_model(league: str) -> MetaEnsembleSportsModel:
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
                f"Modelo cacheado para {league} incompatible ({e!r}). Se re-entrenará en modo rápido."
            )
            try:
                os.remove(model_path)
            except Exception:
                pass

    # Fallback seguro para Serverless Functions (entrenamiento ultrarrápido en <0.5s para evitar timeouts)
    try:
        df_hist = get_historical_dataset(league, n_samples=80)
        X = extract_features(df_hist)
        y_corners = df_hist["total_corners"] if "total_corners" in df_hist.columns else None
        model = MetaEnsembleSportsModel()
        model.fit(X, df_hist["home_win"], df_hist["margin"], df_hist["total_points"], y_corners=y_corners)
        try:
            os.makedirs(MODEL_DIR, exist_ok=True)
            joblib.dump(model, model_path)
        except Exception as e:
            logger.info(f"Sistema de archivos en solo lectura (Serverless): {e}")
        MODELS_CACHE[league] = model
        return model
    except Exception as e:
        logger.error(f"Error entrenando modelo fallback para {league}: {e}")
        model = MetaEnsembleSportsModel()
        MODELS_CACHE[league] = model
        return model


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
                league=league
            )
            fix["prediction"] = prediction
        except Exception as e:
            logger.exception(f"Error prediciendo fixture {fix.get('fixture_id')} ({league})")
            fix["prediction"] = None
            fix["prediction_error"] = str(e)
        enhanced_fixtures.append(fix)

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
    df_hist = get_historical_dataset(req.league, n_samples=1200)
    X = extract_features(df_hist)
    
    # Custom training
    new_model = MetaEnsembleSportsModel(svm_weight=0.15, nn_weight=0.20, rf_weight=0.15, xgb_weight=0.25, lgbm_weight=0.25)
    new_model.svm.c = req.svm_c
    new_model.svm.kernel = req.svm_kernel
    new_model.nn.learning_rate_init = req.nn_learning_rate
    new_model.nn.hidden_layer_sizes = (req.nn_hidden_size, req.nn_hidden_size // 2)

    new_model.fit(X, df_hist["home_win"], df_hist["margin"], df_hist["total_points"])
    
    # Save & Cache
    try:
        os.makedirs(MODEL_DIR, exist_ok=True)
        model_path = os.path.join(MODEL_DIR, f"model_{req.league}.joblib")
        joblib.dump(new_model, model_path)
    except Exception as e:
        logger.info(f"No se pudo guardar el modelo en disco (Read-only filesystem): {e}")
    MODELS_CACHE[req.league] = new_model

    return {
        "message": f"Modelo para {req.league} re-entrenado exitosamente",
        "parameters": req.dict(),
        "status": "ready"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
