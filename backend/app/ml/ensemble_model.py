import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from typing import Dict
from app.ml.svm_model import SVMSportsModel
from app.ml.neural_net_model import NeuralNetworkSportsModel
from app.ml.xgboost_model import XGBoostSportsModel
from app.ml.lightgbm_model import LightGBMSportsModel
from app.ml.data_generator import total_edge_threshold, margin_edge_threshold, corners_edge_threshold

class MetaEnsembleSportsModel:
    def __init__(
        self,
        svm_weight: float = 0.15,
        nn_weight: float = 0.20,
        rf_weight: float = 0.15,
        xgb_weight: float = 0.25,
        lgbm_weight: float = 0.25,
    ):
        self.svm_weight = svm_weight
        self.nn_weight = nn_weight
        self.rf_weight = rf_weight
        self.xgb_weight = xgb_weight
        self.lgbm_weight = lgbm_weight

        self.svm = SVMSportsModel()
        self.nn = NeuralNetworkSportsModel()
        self.xgb = XGBoostSportsModel()
        self.lgbm = LightGBMSportsModel()

        self.rf_classifier = Pipeline([
            ("scaler", StandardScaler()),
            ("rf", RandomForestClassifier(n_estimators=100, max_depth=8, random_state=42))
        ])
        self.rf_spread = Pipeline([
            ("scaler", StandardScaler()),
            ("rf", RandomForestRegressor(n_estimators=100, max_depth=8, random_state=42))
        ])
        self.rf_total = Pipeline([
            ("scaler", StandardScaler()),
            ("rf", RandomForestRegressor(n_estimators=100, max_depth=8, random_state=42))
        ])

        # Regresor de córners totales — solo se entrena para ligas de fútbol
        # (Liga MX) donde sí hay un target de córners disponible.
        self.corners_regressor = Pipeline([
            ("scaler", StandardScaler()),
            ("rf", RandomForestRegressor(n_estimators=100, max_depth=6, random_state=42))
        ])
        self.has_corners_model = False

    def fit(self, X: pd.DataFrame, y_win: pd.Series, y_margin: pd.Series, y_total: pd.Series,
            y_corners: pd.Series = None):
        self.svm.fit(X, y_win, y_margin, y_total)
        self.nn.fit(X, y_win, y_margin, y_total)
        self.xgb.fit(X, y_win, y_margin, y_total)
        self.lgbm.fit(X, y_win, y_margin, y_total)

        self.rf_classifier.fit(X, y_win)
        self.rf_spread.fit(X, y_margin)
        self.rf_total.fit(X, y_total)

        # y_corners puede venir con NaN (partidos donde ESPN no publicó el
        # stat de córners) — se entrena solo con las filas que sí lo tienen.
        if y_corners is not None:
            valid_mask = y_corners.notna()
            if valid_mask.sum() >= 30:  # mínimo razonable de muestras
                self.corners_regressor.fit(X.loc[valid_mask], y_corners.loc[valid_mask])
                self.has_corners_model = True

    def predict_one(self, X: pd.DataFrame, sb_home_odds: float = 1.90, sb_away_odds: float = 1.90,
                     sb_spread: float = 0.0, sb_total: float = 200.0,
                     sb_corners_total: float = None, league: str = None,
                     odds_are_real: bool = False, market_blend_weight: float = 0.35) -> Dict:
        svm_res = self.svm.predict_one(X)
        nn_res = self.nn.predict_one(X)
        xgb_res = self.xgb.predict_one(X)
        lgbm_res = self.lgbm.predict_one(X)

        rf_prob = float(self.rf_classifier.predict_proba(X)[0][1])
        rf_margin = float(self.rf_spread.predict(X)[0])
        rf_total = float(self.rf_total.predict(X)[0])

        w_sum = self.svm_weight + self.nn_weight + self.rf_weight + self.xgb_weight + self.lgbm_weight
        w_svm = self.svm_weight / w_sum
        w_nn = self.nn_weight / w_sum
        w_rf = self.rf_weight / w_sum
        w_xgb = self.xgb_weight / w_sum
        w_lgbm = self.lgbm_weight / w_sum

        ens_home_win_prob = (
            (svm_res["home_win_prob"] * w_svm)
            + (nn_res["home_win_prob"] * w_nn)
            + (rf_prob * w_rf)
            + (xgb_res["home_win_prob"] * w_xgb)
            + (lgbm_res["home_win_prob"] * w_lgbm)
        )
        ens_away_win_prob = 1.0 - ens_home_win_prob

        # --- Mercado como input, no solo como punto de comparación ---
        # Antes, sb_home_odds/sb_away_odds solo se usaban DESPUÉS para
        # calcular el +EV -- el mercado nunca entraba a la predicción en
        # sí. Ahora que hay cuotas REALES disponibles (the-odds-api.com,
        # ver odds_source en data_generator.py), se mezcla la probabilidad
        # del ensemble con la probabilidad implícita del mercado (sin vig)
        # -- el mercado es, empíricamente, uno de los mejores predictores
        # individuales que existen para moneyline. Solo se mezcla cuando
        # odds_are_real=True: mezclar con una cuota ESTIMADA por el propio
        # modelo sería circular (el modelo terminaría "confirmando" su
        # propia opinión, no incorporando información nueva).
        #
        # Importante: esto hace que el +EV detectado después sea MENOR y
        # más selectivo que antes -- es el comportamiento correcto. Un
        # modelo que ya incorporó la opinión del mercado y AÚN así
        # encuentra una diferencia grande es una señal mucho más creíble
        # que una que ignora al mercado por completo.
        model_only_home_win_prob = ens_home_win_prob
        market_implied_home_prob = None
        blended_with_market = False

        if odds_are_real and sb_home_odds and sb_away_odds and sb_home_odds > 1.0 and sb_away_odds > 1.0:
            raw_home = 1.0 / sb_home_odds
            raw_away = 1.0 / sb_away_odds
            overround = raw_home + raw_away  # > 1.0 por el margen (vig) de la casa
            market_implied_home_prob = raw_home / overround  # normalizado a 100%, vig removido

            ens_home_win_prob = (
                (1.0 - market_blend_weight) * ens_home_win_prob
                + market_blend_weight * market_implied_home_prob
            )
            ens_away_win_prob = 1.0 - ens_home_win_prob
            blended_with_market = True

        ens_margin = (
            (svm_res["predicted_margin"] * w_svm)
            + (nn_res["predicted_margin"] * w_nn)
            + (rf_margin * w_rf)
            + (xgb_res["predicted_margin"] * w_xgb)
            + (lgbm_res["predicted_margin"] * w_lgbm)
        )
        ens_total = (
            (svm_res["predicted_total"] * w_svm)
            + (nn_res["predicted_total"] * w_nn)
            + (rf_total * w_rf)
            + (xgb_res["predicted_total"] * w_xgb)
            + (lgbm_res["predicted_total"] * w_lgbm)
        )

        # Value Bet (+EV) Calculation
        # EV = (Prob * Odds) - 1
        ev_home = (ens_home_win_prob * sb_home_odds) - 1.0
        ev_away = (ens_away_win_prob * sb_away_odds) - 1.0

        if ev_home > 0.05 and ev_home >= ev_away:
            best_val_pick = "HOME"
            best_val_ev = round(ev_home * 100, 1)
        elif ev_away > 0.05:
            best_val_pick = "AWAY"
            best_val_ev = round(ev_away * 100, 1)
        else:
            best_val_pick = "NO VALUE"
            best_val_ev = 0.0

        # Over / Under Recommendation
        # El umbral de "hay valor real" depende de la liga: 2.0 tiene sentido
        # para un total de ~220 puntos (NBA), pero en fútbol (~2.7 goles) esa
        # diferencia casi nunca se alcanza y el pick quedaba siempre en PASS.
        total_diff = ens_total - sb_total
        total_threshold = total_edge_threshold(league)
        total_conf_scale = 20.0 if total_threshold < 1.0 else 5.0  # sensibilidad de confianza ajustada a la escala del deporte
        if total_diff >= total_threshold:
            ou_pick = f"OVER {sb_total}"
            ou_confidence = min(95.0, round(50.0 + abs(total_diff) * total_conf_scale, 1))
        elif total_diff <= -total_threshold:
            ou_pick = f"UNDER {sb_total}"
            ou_confidence = min(95.0, round(50.0 + abs(total_diff) * total_conf_scale, 1))
        else:
            ou_pick = "SIN VALOR (línea ajustada)"
            ou_confidence = 50.0

        # Spread recommendation
        cover_margin = ens_margin - (-sb_spread)
        margin_threshold = margin_edge_threshold(league)
        if cover_margin > margin_threshold:
            spread_pick = f"HOME {sb_spread:+g} (cubre el hándicap)"
        elif cover_margin < -margin_threshold:
            spread_pick = f"AWAY {-sb_spread:+g} (cubre el hándicap)"
        else:
            spread_pick = "SIN VENTAJA CLARA (línea pareja)"

        # Córners totales (Over/Under) — solo si el modelo de esta liga
        # fue entrenado con datos de córners (Liga MX)
        corners_block = None
        if self.has_corners_model:
            pred_corners = float(self.corners_regressor.predict(X)[0])
            corners_pick = None
            corners_conf = None
            if sb_corners_total is not None:
                corner_diff = pred_corners - sb_corners_total
                corners_threshold = corners_edge_threshold(league)
                if corner_diff >= corners_threshold:
                    corners_pick = f"OVER {sb_corners_total}"
                    corners_conf = min(95.0, round(50.0 + abs(corner_diff) * 6.0, 1))
                elif corner_diff <= -corners_threshold:
                    corners_pick = f"UNDER {sb_corners_total}"
                    corners_conf = min(95.0, round(50.0 + abs(corner_diff) * 6.0, 1))
                else:
                    corners_pick = "SIN VALOR (línea ajustada)"
                    corners_conf = 50.0
            corners_block = {
                "predicted_corners_total": round(pred_corners, 1),
                "corners_line": sb_corners_total,
                "over_under_pick": corners_pick,
                "over_under_conf": corners_conf,
            }

        return {
            "ensemble": {
                "home_win_prob": round(ens_home_win_prob, 4),
                "away_win_prob": round(ens_away_win_prob, 4),
                "model_only_home_win_prob": round(model_only_home_win_prob, 4),
                "market_implied_home_prob": round(market_implied_home_prob, 4) if market_implied_home_prob is not None else None,
                "blended_with_market": blended_with_market,
                "predicted_winner": "HOME" if ens_home_win_prob >= 0.5 else "AWAY",
                "predicted_margin": round(ens_margin, 2),
                "predicted_spread_line": round(-ens_margin, 1),
                "predicted_total": round(ens_total, 2),
                "confidence": round(abs(ens_home_win_prob - 0.5) * 200.0, 1),
                "value_pick": best_val_pick,
                "value_ev_pct": best_val_ev,
                "over_under_pick": ou_pick,
                "over_under_conf": ou_confidence,
                "spread_pick": spread_pick,
                "corners": corners_block
            },
            "models_breakdown": {
                "SVM": svm_res,
                "NeuralNetwork": nn_res,
                "XGBoost": xgb_res,
                "LightGBM": lgbm_res,
                "RandomForest": {
                    "model_type": "RandomForest",
                    "home_win_prob": round(rf_prob, 4),
                    "away_win_prob": round(1.0 - rf_prob, 4),
                    "predicted_winner": "HOME" if rf_prob >= 0.5 else "AWAY",
                    "predicted_margin": round(rf_margin, 2),
                    "predicted_spread_line": round(-rf_margin, 1),
                    "predicted_total": round(rf_total, 2),
                    "confidence": round(abs(rf_prob - 0.5) * 200.0, 1)
                }
            }
        }
