import numpy as np
import pandas as pd
from sklearn.neural_network import MLPClassifier, MLPRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from typing import Dict, Tuple

class NeuralNetworkSportsModel:
    def __init__(self, hidden_layer_sizes=(64, 32), max_iter: int = 400, learning_rate_init: float = 0.001):
        self.hidden_layer_sizes = hidden_layer_sizes
        self.max_iter = max_iter
        self.learning_rate_init = learning_rate_init

        self.classifier = Pipeline([
            ("scaler", StandardScaler()),
            ("mlp", MLPClassifier(
                hidden_layer_sizes=self.hidden_layer_sizes,
                max_iter=self.max_iter,
                learning_rate_init=self.learning_rate_init,
                activation="relu",
                solver="adam",
                early_stopping=True,
                random_state=42
            ))
        ])

        self.spread_regressor = Pipeline([
            ("scaler", StandardScaler()),
            ("mlp", MLPRegressor(
                hidden_layer_sizes=self.hidden_layer_sizes,
                max_iter=self.max_iter,
                learning_rate_init=self.learning_rate_init,
                activation="relu",
                solver="adam",
                early_stopping=True,
                random_state=42
            ))
        ])

        self.total_regressor = Pipeline([
            ("scaler", StandardScaler()),
            ("mlp", MLPRegressor(
                hidden_layer_sizes=self.hidden_layer_sizes,
                max_iter=self.max_iter,
                learning_rate_init=self.learning_rate_init,
                activation="relu",
                solver="adam",
                early_stopping=True,
                random_state=42
            ))
        ])

    def fit(self, X: pd.DataFrame, y_win: pd.Series, y_margin: pd.Series, y_total: pd.Series):
        self.classifier.fit(X, y_win)
        self.spread_regressor.fit(X, y_margin)
        self.total_regressor.fit(X, y_total)

    def predict_one(self, X: pd.DataFrame) -> Dict:
        win_prob = float(self.classifier.predict_proba(X)[0][1])
        predicted_winner = 1 if win_prob >= 0.5 else 0
        predicted_spread = float(self.spread_regressor.predict(X)[0])
        predicted_total = float(self.total_regressor.predict(X)[0])

        return {
            "model_type": "NeuralNetwork",
            "home_win_prob": round(win_prob, 4),
            "away_win_prob": round(1.0 - win_prob, 4),
            "predicted_winner": "HOME" if predicted_winner == 1 else "AWAY",
            "predicted_margin": round(predicted_spread, 2),
            "predicted_spread_line": round(-predicted_spread, 1),
            "predicted_total": round(predicted_total, 2),
            "confidence": round(abs(win_prob - 0.5) * 200.0, 1)
        }
