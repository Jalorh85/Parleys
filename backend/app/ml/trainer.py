import os
import joblib
import pandas as pd
import numpy as np
from sklearn.metrics import accuracy_score, mean_absolute_error, roc_auc_score
from app.ml.data_generator import generate_historical_dataset
from app.ml.feature_engineering import extract_features
from app.ml.ensemble_model import MetaEnsembleSportsModel

MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "models")

def train_and_save_all_leagues():
    os.makedirs(MODEL_DIR, exist_ok=True)
    leagues = ["LCUP", "MLB", "WNBA", "KBO", "MX"]
    results = {}

    for league in leagues:
        print(f"--- Entrenando modelos de Machine Learning para {league} ---")
        df_hist = generate_historical_dataset(league, n_samples=1500)
        X = extract_features(df_hist)
        y_win = df_hist["home_win"]
        y_margin = df_hist["margin"]
        y_total = df_hist["total_points"]
        y_corners = df_hist["total_corners"] if "total_corners" in df_hist.columns else None

        # Train/Test Split (80/20)
        split_idx = int(len(df_hist) * 0.8)
        X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
        y_win_train, y_win_test = y_win.iloc[:split_idx], y_win.iloc[split_idx:]
        y_margin_train, y_margin_test = y_margin.iloc[:split_idx], y_margin.iloc[split_idx:]
        y_total_train, y_total_test = y_total.iloc[:split_idx], y_total.iloc[split_idx:]
        y_corners_train = y_corners.iloc[:split_idx] if y_corners is not None else None

        # Create Model
        ensemble_model = MetaEnsembleSportsModel(svm_weight=0.4, nn_weight=0.4, rf_weight=0.2)
        ensemble_model.fit(X_train, y_win_train, y_margin_train, y_total_train, y_corners=y_corners_train)

        # Evaluate Individual Models
        svm_preds = [ensemble_model.svm.predict_one(X_test.iloc[[i]]) for i in range(len(X_test))]
        nn_preds = [ensemble_model.nn.predict_one(X_test.iloc[[i]]) for i in range(len(X_test))]
        
        # Test Ensemble
        test_df = df_hist.iloc[split_idx:].reset_index(drop=True)
        ens_preds = []
        for i in range(len(test_df)):
            row = test_df.iloc[i]
            x_single = X_test.iloc[[i]]
            res = ensemble_model.predict_one(
                x_single,
                sb_home_odds=row["sb_home_odds"],
                sb_away_odds=row["sb_away_odds"],
                sb_spread=row["sb_spread"],
                sb_total=row["sb_total"],
                sb_corners_total=row.get("sb_corners_total"),
                league=league
            )
            ens_preds.append(res)

        # Calculate Metrics
        # Winner accuracy
        svm_win_acc = round(accuracy_score(y_win_test, [1 if p["predicted_winner"] == "HOME" else 0 for p in svm_preds]) * 100, 2)
        nn_win_acc = round(accuracy_score(y_win_test, [1 if p["predicted_winner"] == "HOME" else 0 for p in nn_preds]) * 100, 2)
        ens_win_acc = round(accuracy_score(y_win_test, [1 if p["ensemble"]["predicted_winner"] == "HOME" else 0 for p in ens_preds]) * 100, 2)

        # Spread & Total MAE
        svm_tot_mae = round(mean_absolute_error(y_total_test, [p["predicted_total"] for p in svm_preds]), 2)
        nn_tot_mae = round(mean_absolute_error(y_total_test, [p["predicted_total"] for p in nn_preds]), 2)
        ens_tot_mae = round(mean_absolute_error(y_total_test, [p["ensemble"]["predicted_total"] for p in ens_preds]), 2)

        # Save Model
        model_path = os.path.join(MODEL_DIR, f"model_{league}.joblib")
        joblib.dump(ensemble_model, model_path)

        results[league] = {
            "svm_win_acc": svm_win_acc,
            "nn_win_acc": nn_win_acc,
            "ens_win_acc": ens_win_acc,
            "svm_tot_mae": svm_tot_mae,
            "nn_tot_mae": nn_tot_mae,
            "ens_tot_mae": ens_tot_mae,
            "train_samples": len(X_train),
            "test_samples": len(X_test),
            "saved_to": model_path
        }

    return results

if __name__ == "__main__":
    metrics = train_and_save_all_leagues()
    print("Entrenamiento completado exitosamente:", metrics)
