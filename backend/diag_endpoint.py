"""Diagnóstico: simula exactamente lo que hace el endpoint /api/fixtures"""
import sys
sys.path.insert(0, '.')

from app.ml.data_generator import get_upcoming_fixtures
from app.ml.feature_engineering import dict_to_features
from app.ml.ensemble_model import MetaEnsembleSportsModel
from app.ml.data_generator import generate_historical_dataset
from app.ml.feature_engineering import extract_features
from datetime import date, timedelta

manana = date.today() + timedelta(days=1)

for liga in ["NBA", "MLB", "WNBA", "KBO"]:
    print(f"\n=== {liga} ===")
    try:
        fixtures = get_upcoming_fixtures(liga, manana)
        print(f"  Fixtures generados: {len(fixtures)}")
        if fixtures:
            print(f"  Fuente: {fixtures[0]['source']}")
            print(f"  Primer partido: {fixtures[0]['home_team']} vs {fixtures[0]['away_team']}")
            # Probar dict_to_features
            try:
                X = dict_to_features(fixtures[0])
                print(f"  dict_to_features: OK (shape {X.shape})")
            except Exception as e:
                print(f"  dict_to_features ERROR: {e}")
        else:
            print("  *** LISTA VACÍA - este es el problema ***")
    except Exception as e:
        print(f"  ERROR en get_upcoming_fixtures: {e}")
        import traceback
        traceback.print_exc()
