import pandas as pd
import numpy as np
from typing import Dict, List
from app.ml.feature_engineering import extract_features
from app.ml.ensemble_model import MetaEnsembleSportsModel

def run_backtest(
    model: MetaEnsembleSportsModel,
    df: pd.DataFrame,
    initial_bankroll: float = 1000.0,
    staking_strategy: str = "kelly", # "kelly" or "flat"
    flat_stake_pct: float = 0.03, # 3% bankroll per bet
    min_ev_pct: float = 2.0, # Minimum +2% EV to place bet
    min_confidence: float = 10.0 # Minimum 10% model confidence
) -> Dict:
    bankroll = initial_bankroll
    bankroll_history = [bankroll]

    total_bets = 0
    winning_bets = 0
    total_staked = 0.0
    net_profit = 0.0

    trades = []

    X = extract_features(df)

    for i in range(len(df)):
        row = df.iloc[i]
        x_single = X.iloc[[i]]

        sb_home_odds = float(row.get("sb_home_odds", 1.90))
        sb_away_odds = float(row.get("sb_away_odds", 1.90))
        sb_spread = float(row.get("sb_spread", 0.0))
        sb_total = float(row.get("sb_total", 200.0))

        actual_win = int(row["home_win"]) # 1 home, 0 away
        actual_margin = float(row["margin"])
        actual_total = float(row["total_points"])

        pred = model.predict_one(x_single, sb_home_odds, sb_away_odds, sb_spread, sb_total)
        ens = pred["ensemble"]

        prob_home = ens["home_win_prob"]
        prob_away = ens["away_win_prob"]

        ev_home = (prob_home * sb_home_odds) - 1.0
        ev_away = (prob_away * sb_away_odds) - 1.0

        best_pick = None
        best_ev = 0.0
        odds = 1.0
        prob = 0.5
        won = False

        if ev_home > (min_ev_pct / 100.0) and ev_home >= ev_away and ens["confidence"] >= min_confidence:
            best_pick = "HOME"
            best_ev = ev_home
            odds = sb_home_odds
            prob = prob_home
            won = (actual_win == 1)
        elif ev_away > (min_ev_pct / 100.0) and ens["confidence"] >= min_confidence:
            best_pick = "AWAY"
            best_ev = ev_away
            odds = sb_away_odds
            prob = prob_away
            won = (actual_win == 0)

        if best_pick is not None:
            # Calculate Stake
            if staking_strategy == "kelly":
                # Kelly formula: f* = (bp - q) / b
                b = odds - 1.0
                q = 1.0 - prob
                f_kelly = ((b * prob) - q) / b if b > 0 else 0.0
                # Fractional Kelly (25% Kelly for risk safety)
                stake_pct = max(0.005, min(0.05, f_kelly * 0.25))
            else: # flat
                stake_pct = flat_stake_pct

            stake = round(bankroll * stake_pct, 2)
            if stake > bankroll:
                stake = bankroll

            if stake > 0:
                total_bets += 1
                total_staked += stake

                if won:
                    profit = round(stake * (odds - 1.0), 2)
                    winning_bets += 1
                else:
                    profit = -stake

                bankroll += profit
                net_profit += profit

                trades.append({
                    "game": f"{row['home_team']} vs {row['away_team']}",
                    "pick": best_pick,
                    "odds": odds,
                    "prob": round(prob, 3),
                    "ev_pct": round(best_ev * 100, 1),
                    "stake": stake,
                    "profit": profit,
                    "won": won,
                    "bankroll": round(bankroll, 2)
                })

        bankroll_history.append(round(bankroll, 2))

    # Calculate metrics
    win_rate = round((winning_bets / total_bets * 100.0), 1) if total_bets > 0 else 0.0
    roi_pct = round((net_profit / total_staked * 100.0), 2) if total_staked > 0 else 0.0
    
    # Max Drawdown
    b_arr = np.array(bankroll_history)
    peak = np.maximum.accumulate(b_arr)
    drawdown = (peak - b_arr) / peak
    max_drawdown_pct = round(float(np.max(drawdown)) * 100.0, 2) if len(drawdown) > 0 else 0.0

    return {
        "initial_bankroll": initial_bankroll,
        "final_bankroll": round(bankroll, 2),
        "net_profit": round(net_profit, 2),
        "roi_pct": roi_pct,
        "total_bets": total_bets,
        "winning_bets": winning_bets,
        "win_rate": win_rate,
        "total_staked": round(total_staked, 2),
        "max_drawdown_pct": max_drawdown_pct,
        "bankroll_progression": bankroll_history[::max(1, len(bankroll_history)//40)],
        "recent_trades": trades[-10:]
    }
