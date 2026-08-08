import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from typing import Dict

try:
    from xgboost import XGBClassifier as _XGBClassifier, XGBRegressor as _XGBRegressor
    HAS_REAL_XGBOOST = True
except Exception:
    from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
    HAS_REAL_XGBOOST = False

    # HistGradientBoosting* no acepta n_estimators/subsample/colsample_bytree/
    # eval_metric (los nombres de parámetro de XGBoost) — solo max_iter y
    # similares. Este wrapper traduce lo que sí aplica y descarta el resto,
    # para que el fallback no reviente con "unexpected keyword argument"
    # cuando xgboost no está instalado.
    def _XGBClassifier(n_estimators=150, max_depth=4, learning_rate=0.08, random_state=42, **_ignored):
        return HistGradientBoostingClassifier(
            max_iter=n_estimators,
            max_depth=max_depth,
            learning_rate=learning_rate,
            random_state=random_state,
        )

    def _XGBRegressor(n_estimators=150, max_depth=4, learning_rate=0.08, random_state=42, **_ignored):
        return HistGradientBoostingRegressor(
            max_iter=n_estimators,
            max_depth=max_depth,
            learning_rate=learning_rate,
            random_state=random_state,
        )

class XGBoostSportsModel:
    def __init__(self, n_estimators: int = 150, max_depth: int = 4, learning_rate: float = 0.08):
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.learning_rate = learning_rate

        self.classifier = Pipeline([
            ("scaler", StandardScaler()),
            ("xgb", _XGBClassifier(
                n_estimators=self.n_estimators,
                max_depth=self.max_depth,
                learning_rate=self.learning_rate,
                subsample=0.85,
                colsample_bytree=0.85,
                eval_metric="logloss",
                random_state=42
            ))
        ])

        self.spread_regressor = Pipeline([
            ("scaler", StandardScaler()),
            ("xgb", _XGBRegressor(
                n_estimators=self.n_estimators,
                max_depth=self.max_depth,
                learning_rate=self.learning_rate,
                subsample=0.85,
                colsample_bytree=0.85,
                random_state=42
            ))
        ])

        self.total_regressor = Pipeline([
            ("scaler", StandardScaler()),
            ("xgb", _XGBRegressor(
                n_estimators=self.n_estimators,
                max_depth=self.max_depth,
                learning_rate=self.learning_rate,
                subsample=0.85,
                colsample_bytree=0.85,
                random_state=42
            ))
        ])

    def fit(self, X: pd.DataFrame, y_win: pd.Series, y_margin: pd.Series, y_total: pd.Series):
        self.classifier.fit(X, y_win)
        self.spread_regressor.fit(X, y_margin)
        self.total_regressor.fit(X, y_total)

    def predict_one(self, X: pd.DataFrame) -> Dict:
        win_prob = float(self.classifier.predict_proba(X)[0][1])  # Prob de victoria local
        predicted_winner = 1 if win_prob >= 0.5 else 0
        predicted_spread = float(self.spread_regressor.predict(X)[0])
        predicted_total = float(self.total_regressor.predict(X)[0])

        return {
            "model_type": "XGBoost",
            "home_win_prob": round(win_prob, 4),
            "away_win_prob": round(1.0 - win_prob, 4),
            "predicted_winner": "HOME" if predicted_winner == 1 else "AWAY",
            "predicted_margin": round(predicted_spread, 2),
            "predicted_spread_line": round(-predicted_spread, 1),
            "predicted_total": round(predicted_total, 2),
            "confidence": round(abs(win_prob - 0.5) * 200.0, 1)
        }
