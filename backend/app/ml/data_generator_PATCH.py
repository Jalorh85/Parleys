"""
PATCH para data_generator.py

Cambios:
1. _enrich_fixture_with_profiles ahora acepta home_pitcher_era_real /
   away_pitcher_era_real. Si vienen (no None), se usan tal cual en vez del
   rng.normal() simulado.
2. get_upcoming_fixtures pasa esos valores desde el fixture real de ESPN.
"""

# --- Reemplaza la firma y el bloque de ERA dentro de _enrich_fixture_with_profiles ---

def _enrich_fixture_with_profiles(home_team: str, away_team: str, league: str,
                                  date_str: str, idx: int,
                                  fixture_id: str = None,
                                  time_str: str = "TBD",
                                  source: str = "Simulado",
                                  home_pitcher_era_real=None,
                                  away_pitcher_era_real=None,
                                  **kwargs) -> Dict:
    profiles = generate_team_profiles(league)
    mean_tot, _ = LEAGUE_BASE_TOTALS.get(league, (200.0, 10.0))

    seed = hash(f"{date_str}{home_team}{away_team}") % (2**31)
    rng = np.random.default_rng(seed)

    h_prof = profiles.get(home_team, {"off_rating": 100, "def_rating": 100, "home_adv": 3.0, "pace": 100, "pitching_era": 3.85})
    a_prof = profiles.get(away_team, {"off_rating": 100, "def_rating": 100, "home_adv": 0.0, "pace": 100, "pitching_era": 3.95})

    home_rest = int(rng.choice([0, 1, 2, 3], p=[0.2, 0.5, 0.2, 0.1]))
    away_rest = int(rng.choice([0, 1, 2, 3], p=[0.25, 0.5, 0.2, 0.05]))
    home_form = round(float(np.clip(rng.normal(0.58, 0.15), 0.1, 0.95)), 2)
    away_form = round(float(np.clip(rng.normal(0.50, 0.15), 0.1, 0.95)), 2)

    h_pitcher = f"Pitcher {home_team[:3].upper()}" if league in ["MLB", "KBO"] else "N/A"
    a_pitcher = f"Pitcher {away_team[:3].upper()}" if league in ["MLB", "KBO"] else "N/A"

    # --- ERA: usar la real de ESPN si está disponible, si no, estimar ---
    era_is_real = False
    if league in ["MLB", "KBO"]:
        if home_pitcher_era_real is not None and away_pitcher_era_real is not None:
            h_era = round(float(home_pitcher_era_real), 2)
            a_era = round(float(away_pitcher_era_real), 2)
            era_is_real = True
        else:
            h_era = round(float(rng.normal(h_prof.get("pitching_era", 3.85), 0.5)), 2)
            a_era = round(float(rng.normal(a_prof.get("pitching_era", 3.95), 0.5)), 2)
    else:
        h_era = 0.0
        a_era = 0.0

    exp_margin = (
        (h_prof["off_rating"] - a_prof["off_rating"]) * 0.25
        + h_prof["home_adv"]
        + (home_form - away_form) * 8
    )
    sb_spread = round(-exp_margin, 1)
    sb_total = round(mean_tot + (h_prof["off_rating"] + a_prof["off_rating"] - 200) * 0.3, 1)

    p_home = 1 / (1 + np.exp(-exp_margin / 8.0))
    sb_home_odds = round(float(1.0 / p_home if p_home > 0.05 else 12.0), 2)
    sb_away_odds = round(float(1.0 / (1 - p_home) if p_home < 0.95 else 12.0), 2)

    return {
        "fixture_id": fixture_id or f"FIX-{league}-{date_str}-{idx}",
        "date": date_str,
        "time": time_str,
        "league": league,
        "home_team": home_team,
        "away_team": away_team,
        "home_rest": home_rest,
        "away_rest": away_rest,
        "home_form": home_form,
        "away_form": away_form,
        "h_pitcher": h_pitcher,
        "a_pitcher": a_pitcher,
        "h_pitcher_era": h_era,
        "a_pitcher_era": a_era,
        "pitcher_era_is_real": era_is_real,   # útil para mostrar un badge en el frontend
        "home_off_rating": h_prof["off_rating"],
        "away_off_rating": a_prof["off_rating"],
        "home_def_rating": h_prof["def_rating"],
        "away_def_rating": a_prof["def_rating"],
        "home_adv": h_prof["home_adv"],
        "pace": h_prof["pace"],
        "sb_home_odds": sb_home_odds,
        "sb_away_odds": sb_away_odds,
        "sb_spread": sb_spread,
        "sb_total": sb_total,
        "source": source,
        "home_logo": kwargs.get("home_logo", ""),
        "away_logo": kwargs.get("away_logo", ""),
    }


# --- Dentro de get_upcoming_fixtures, en el bloque "if real_fixtures:" ---
# Reemplaza la llamada a _enrich_fixture_with_profiles por esta versión,
# que propaga el ERA real cuando existe:

def get_upcoming_fixtures_REAL_FIXTURES_BLOCK(real_fixtures, league, date_str):
    """Fragmento ilustrativo — pega esta lógica dentro de get_upcoming_fixtures."""
    enriched = []
    for idx, fix in enumerate(real_fixtures):
        enriched.append(_enrich_fixture_with_profiles(
            home_team=fix["home_team"],
            away_team=fix["away_team"],
            league=league,
            date_str=date_str,
            idx=idx,
            fixture_id=fix["fixture_id"],
            time_str=fix.get("time", "TBD"),
            source=fix.get("source", "API"),
            home_logo=fix.get("home_logo", ""),
            away_logo=fix.get("away_logo", ""),
            home_pitcher_era_real=fix.get("home_pitcher_era_real"),
            away_pitcher_era_real=fix.get("away_pitcher_era_real"),
        ))
    return enriched
