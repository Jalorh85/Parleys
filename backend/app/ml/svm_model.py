import numpy as np
import pandas as pd
from sklearn.svm import SVC, SVR
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from typing import Dict, Tuple

class SVMSportsModel:
    def __init__(self, kernel: str = "rbf", c: float = 1.0, gamma: str = "scale"):
        self.kernel = kernel
        self.c = c
        self.gamma = gamma

        self.classifier = Pipeline([
            ("scaler", StandardScaler()),
            ("svm", SVC(kernel=self.kernel, C=self.c, gamma=self.gamma, probability=True, random_state=42))
        ])

        self.spread_regressor = Pipeline([
            ("scaler", StandardScaler()),
            ("svr", SVR(kernel=self.kernel, C=self.c, gamma=self.gamma))
        ])

        self.total_regressor = Pipeline([
            ("scaler", StandardScaler()),
            ("svr", SVR(kernel=self.kernel, C=self.c, gamma=self.gamma))
        ])

    def fit(self, X: pd.DataFrame, y_win: pd.Series, y_margin: pd.Series, y_total: pd.Series):
        self.classifier.fit(X, y_win)
        self.spread_regressor.fit(X, y_margin)
        self.total_regressor.fit(X, y_total)

    def predict_one(self, X: pd.DataFrame) -> Dict:
        win_prob = float(self.classifier.predict_proba(X)[0][1]) # Prob of home win
        predicted_winner = 1 if win_prob >= 0.5 else 0
        predicted_spread = float(self.spread_regressor.predict(X)[0]) # predicted home margin
        predicted_total = float(self.total_regressor.predict(X)[0])

        return {
            "model_type": "SVM",
            "home_win_prob": round(win_prob, 4),
            "away_win_prob": round(1.0 - win_prob, 4),
            "predicted_winner": "HOME" if predicted_winner == 1 else "AWAY",
            "predicted_margin": round(predicted_spread, 2),
            "predicted_spread_line": round(-predicted_spread, 1),
            "predicted_total": round(predicted_total, 2),
            "confidence": round(abs(win_prob - 0.5) * 200.0, 1) # 0 to 100% confidence
        }
