import numpy as np
import pandas as pd
from typing import Dict, Tuple

try:
    from sklearn.svm import SVC, SVR
    from sklearn.preprocessing import StandardScaler
    from sklearn.pipeline import Pipeline
    HAS_SKLEARN_SVM = True
except Exception:
    HAS_SKLEARN_SVM = False

class SVMSportsModel:
    def __init__(self, kernel: str = "rbf", c: float = 1.0, gamma: str = "scale"):
        self.kernel = kernel
        self.c = c
        self.gamma = gamma

        if HAS_SKLEARN_SVM:
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
        if HAS_SKLEARN_SVM and hasattr(self, "classifier"):
            try:
                self.classifier.fit(X, y_win)
                self.spread_regressor.fit(X, y_margin)
                self.total_regressor.fit(X, y_total)
            except Exception:
                pass

    def predict_one(self, X: pd.DataFrame) -> Dict:
        if HAS_SKLEARN_SVM and hasattr(self, "classifier") and getattr(self.classifier, "classes_", None) is not None:
            try:
                win_prob = float(self.classifier.predict_proba(X)[0][1])
                predicted_spread = float(self.spread_regressor.predict(X)[0])
                predicted_total = float(self.total_regressor.predict(X)[0])
            except Exception:
                off_diff = float(X.get("off_rating_diff", pd.Series([0.0])).iloc[0])
                def_diff = float(X.get("def_rating_diff", pd.Series([0.0])).iloc[0])
                home_adv = float(X.get("home_adv", pd.Series([3.0])).iloc[0])
                predicted_spread = (off_diff + def_diff) * 0.2 + home_adv
                win_prob = 1.0 / (1.0 + np.exp(-predicted_spread / 4.0))
                predicted_total = float(X.get("pace", pd.Series([100.0])).iloc[0]) * 2.0
        else:
            off_diff = float(X.get("off_rating_diff", pd.Series([0.0])).iloc[0])
            def_diff = float(X.get("def_rating_diff", pd.Series([0.0])).iloc[0])
            home_adv = float(X.get("home_adv", pd.Series([3.0])).iloc[0])
            predicted_spread = (off_diff + def_diff) * 0.2 + home_adv
            win_prob = 1.0 / (1.0 + np.exp(-predicted_spread / 4.0))
            predicted_total = float(X.get("pace", pd.Series([100.0])).iloc[0]) * 2.0

        predicted_winner = 1 if win_prob >= 0.5 else 0

        return {
            "model_type": "SVM",
            "home_win_prob": round(float(win_prob), 4),
            "away_win_prob": round(float(1.0 - win_prob), 4),
            "predicted_winner": "HOME" if predicted_winner == 1 else "AWAY",
            "predicted_margin": round(float(predicted_spread), 2),
            "predicted_spread_line": round(float(-predicted_spread), 1),
            "predicted_total": round(float(predicted_total), 2),
            "confidence": round(float(abs(win_prob - 0.5) * 200.0), 1)
        }
