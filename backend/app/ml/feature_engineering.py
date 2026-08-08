import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from typing import Tuple, List, Dict

FEATURE_COLS = [
    "off_rating_diff",
    "def_rating_diff",
    "home_adv",
    "rest_diff",
    "form_diff",
    "pitcher_era_diff",
    "pace"
]

def extract_features(df: pd.DataFrame) -> pd.DataFrame:
    X = pd.DataFrame()
    X["off_rating_diff"] = df["home_off_rating"] - df["away_off_rating"]
    X["def_rating_diff"] = df["away_def_rating"] - df["home_def_rating"]
    X["home_adv"] = df["home_adv"]
    X["rest_diff"] = df["home_rest"] - df["away_rest"]
    X["form_diff"] = df["home_form"] - df["away_form"]
    X["pitcher_era_diff"] = df["a_pitcher_era"] - df["h_pitcher_era"]
    X["pace"] = df["pace"]
    return X

def dict_to_features(d: Dict) -> pd.DataFrame:
    row = {
        "home_off_rating": d.get("home_off_rating", 100.0),
        "away_off_rating": d.get("away_off_rating", 100.0),
        "home_def_rating": d.get("home_def_rating", 100.0),
        "away_def_rating": d.get("away_def_rating", 100.0),
        "home_adv": d.get("home_adv", 3.0),
        "home_rest": d.get("home_rest", 1),
        "away_rest": d.get("away_rest", 1),
        "home_form": d.get("home_form", 0.5),
        "away_form": d.get("away_form", 0.5),
        "h_pitcher_era": d.get("h_pitcher_era", 0.0),
        "a_pitcher_era": d.get("a_pitcher_era", 0.0),
        "pace": d.get("pace", 100.0)
    }
    df = pd.DataFrame([row])
    return extract_features(df)
