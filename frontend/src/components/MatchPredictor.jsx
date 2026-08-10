import React, { useState, useEffect } from 'react';
import { Cpu, Play, Award, HelpCircle } from 'lucide-react';
import { predictMatchup } from '../services/api';
import TeamIcon from './TeamIcon';

export default function MatchPredictor({ activeLeague, leagues }) {
  const leagueData = leagues[activeLeague] || { teams: [] };
  const teams = leagueData.teams || [];

  const [homeTeam, setHomeTeam] = useState(teams[0] || 'Team A');
  const [awayTeam, setAwayTeam] = useState(teams[1] || 'Team B');

  useEffect(() => {
    if (teams.length >= 2) {
      setHomeTeam(teams[0]);
      setAwayTeam(teams[1]);
    }
  }, [activeLeague, teams]);

  const [homeRest, setHomeRest] = useState(1);
  const [awayRest, setAwayRest] = useState(1);
  const [homeForm, setHomeForm] = useState(0.65);
  const [awayForm, setAwayForm] = useState(0.50);

  const [hPitcherEra, setHPitcherEra] = useState(3.50);
  const [aPitcherEra, setAPitcherEra] = useState(4.10);

  const [sbHomeOdds, setSbHomeOdds] = useState(1.85);
  const [sbAwayOdds, setSbAwayOdds] = useState(2.05);
  const [sbSpread, setSbSpread] = useState(-3.5);
  const isBaseballDefault = activeLeague === 'MLB' || activeLeague === 'KBO';
  const [sbTotal, setSbTotal] = useState(isBaseballDefault ? 8.5 : (activeLeague === 'NFL' ? 43.5 : 218.5));

  const [predictionResult, setPredictionResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const isBaseball = activeLeague === 'MLB' || activeLeague === 'KBO';

  const handleRunPrediction = async () => {
    setLoading(true);
    try {
      const payload = {
        league: activeLeague,
        home_team: homeTeam,
        away_team: awayTeam,
        home_rest: Number(homeRest),
        away_rest: Number(awayRest),
        home_form: Number(homeForm),
        away_form: Number(awayForm),
        h_pitcher_era: Number(hPitcherEra),
        a_pitcher_era: Number(aPitcherEra),
        sb_home_odds: Number(sbHomeOdds),
        sb_away_odds: Number(sbAwayOdds),
        sb_spread: Number(sbSpread),
        sb_total: Number(sbTotal)
      };
      const res = await predictMatchup(payload);
      setPredictionResult(res.prediction);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (teams.length >= 2) {
      handleRunPrediction();
    }
  }, [activeLeague, homeTeam, awayTeam]);

  const ens = predictionResult?.ensemble || {};
  const models = predictionResult?.models_breakdown || {};

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.2fr', gap: '1.5rem', alignItems: 'start' }}>
      {/* Simulation Form Panel */}
      <div className="glass-panel" style={{ padding: '1.5rem' }}>
        <h2 style={{ fontSize: '1.2rem', fontWeight: 700, marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Cpu color="#2F8FFF" size={22} /> Configurar Enfrentamiento (1v1)
        </h2>

        {/* Teams Selectors */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1.2rem' }}>
          <div style={{ textAlign: 'center' }}>
            <TeamIcon teamName={homeTeam} size={52} />
            <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>Equipo Local (Home)</label>
            <select value={homeTeam} onChange={e => setHomeTeam(e.target.value)} style={{ width: '100%' }}>
              {teams.map(t => (
                <option key={t} value={t} disabled={t === awayTeam}>{t}</option>
              ))}
            </select>
          </div>

          <div style={{ textAlign: 'center' }}>
            <TeamIcon teamName={awayTeam} size={52} />
            <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>Equipo Visitante (Away)</label>
            <select value={awayTeam} onChange={e => setAwayTeam(e.target.value)} style={{ width: '100%' }}>
              {teams.map(t => (
                <option key={t} value={t} disabled={t === homeTeam}>{t}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Form & Rest Sliders */}
        <div style={{ background: 'rgba(0,0,0,0.2)', padding: '1rem', borderRadius: '12px', marginBottom: '1rem' }}>
          <h4 style={{ fontSize: '0.85rem', color: 'var(--accent-cyan)', marginBottom: '0.8rem' }}>Forma Reciente (Últimos 10 Juegos)</h4>
          
          <div style={{ marginBottom: '0.8rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem' }}>
              <span>{homeTeam}:</span>
              <strong>{(homeForm * 100).toFixed(0)}% de Victorias</strong>
            </div>
            <input type="range" min="0.1" max="0.95" step="0.05" value={homeForm} onChange={e => setHomeForm(e.target.value)} style={{ width: '100%' }} />
          </div>

          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem' }}>
              <span>{awayTeam}:</span>
              <strong>{(awayForm * 100).toFixed(0)}% de Victorias</strong>
            </div>
            <input type="range" min="0.1" max="0.95" step="0.05" value={awayForm} onChange={e => setAwayForm(e.target.value)} style={{ width: '100%' }} />
          </div>
        </div>

        {/* Baseball pitcher stats if applicable */}
        {isBaseball && (
          <div style={{ background: 'rgba(0,0,0,0.2)', padding: '1rem', borderRadius: '12px', marginBottom: '1rem' }}>
            <h4 style={{ fontSize: '0.85rem', color: 'var(--accent-gold)', marginBottom: '0.8rem' }}>Estadísticas de Lanzadores Iniciales (ERA)</h4>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.8rem' }}>
              <div>
                <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>ERA Pitcher Local</label>
                <input type="number" step="0.1" value={hPitcherEra} onChange={e => setHPitcherEra(e.target.value)} style={{ width: '100%' }} />
              </div>
              <div>
                <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>ERA Pitcher Visitante</label>
                <input type="number" step="0.1" value={aPitcherEra} onChange={e => setAPitcherEra(e.target.value)} style={{ width: '100%' }} />
              </div>
            </div>
          </div>
        )}

        {/* Bookmaker Odds Inputs */}
        <div style={{ background: 'rgba(0,0,0,0.2)', padding: '1rem', borderRadius: '12px', marginBottom: '1.2rem' }}>
          <h4 style={{ fontSize: '0.85rem', color: 'var(--text-main)', marginBottom: '0.8rem' }}>Cuotas & Líneas de Casa de Apuestas</h4>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.8rem', marginBottom: '0.8rem' }}>
            <div>
              <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Cuota Local (ML)</label>
              <input type="number" step="0.05" value={sbHomeOdds} onChange={e => setSbHomeOdds(e.target.value)} style={{ width: '100%' }} />
            </div>
            <div>
              <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Cuota Visitante (ML)</label>
              <input type="number" step="0.05" value={sbAwayOdds} onChange={e => setSbAwayOdds(e.target.value)} style={{ width: '100%' }} />
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.8rem' }}>
            <div>
              <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Línea Handicap/Spread</label>
              <input type="number" step="0.5" value={sbSpread} onChange={e => setSbSpread(e.target.value)} style={{ width: '100%' }} />
            </div>
            <div>
              <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Línea Total Over/Under</label>
              <input type="number" step="0.5" value={sbTotal} onChange={e => setSbTotal(e.target.value)} style={{ width: '100%' }} />
            </div>
          </div>
        </div>

        <button onClick={handleRunPrediction} className="btn-primary" style={{ width: '100%', justifyContent: 'center' }} disabled={loading}>
          <Play size={18} /> {loading ? 'Calculando con ML...' : 'Ejecutar Inferencia ML'}
        </button>
      </div>

      {/* Prediction Output Results Panel */}
      <div className="glass-panel" style={{ padding: '1.5rem' }}>
        <h2 style={{ fontSize: '1.2rem', fontWeight: 700, marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Award color="#fbbf24" size={22} /> Dictamen del Meta-Ensemble ML
        </h2>

        {predictionResult ? (
          <div>
            {/* Winner Gauge Box */}
            <div style={{ background: 'linear-gradient(135deg, rgba(47, 143, 255, 0.1) 0%, rgba(20, 95, 209, 0.1) 100%)', border: '1px solid rgba(47, 143, 255, 0.3)', borderRadius: '16px', padding: '1.2rem', marginBottom: '1.2rem', textAlign: 'center' }}>
              <TeamIcon teamName={ens.predicted_winner === 'HOME' ? homeTeam : awayTeam} size={58} />
              
              <span className="badge badge-ev" style={{ marginBottom: '0.5rem', display: 'inline-block' }}>
                Confianza de Predicción: {ens.confidence}%
              </span>

              <h3 style={{ fontSize: '1.8rem', fontWeight: 800, marginTop: '0.2rem' }}>
                <span style={{ color: '#00f2fe' }}>
                  {ens.predicted_winner === 'HOME' ? homeTeam : awayTeam}
                </span>
              </h3>
              <p style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>
                Probabilidad Calculada: <strong>{((ens.predicted_winner === 'HOME' ? ens.home_win_prob : ens.away_win_prob) * 100).toFixed(1)}%</strong>
              </p>

              {/* Value Bet Callout */}
              {ens.value_ev_pct > 0 && (
                <div style={{ marginTop: '0.8rem', background: 'rgba(251, 191, 36, 0.15)', border: '1px dashed #fbbf24', padding: '0.6rem', borderRadius: '10px', fontSize: '0.85rem', color: '#fbbf24', fontWeight: 600 }}>
                  🚀 ¡APUESTA CON VALOR DETECTADA! EV Estimado: +{ens.value_ev_pct}%
                </div>
              )}
            </div>

            {/* Model Comparison Breakdown: SVM vs Neural Network vs Random Forest */}
            <h4 style={{ fontSize: '0.9rem', fontWeight: 700, marginBottom: '0.8rem' }}>Desglose por Algoritmo de Machine Learning:</h4>
            
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '0.8rem', marginBottom: '1.2rem' }}>
              {/* SVM Card */}
              <div style={{ background: 'rgba(0,0,0,0.3)', padding: '0.8rem', borderRadius: '12px', borderTop: '3px solid #2F8FFF' }}>
                <div style={{ fontSize: '0.8rem', fontWeight: 700, color: '#2F8FFF' }}>Support Vector Machine (SVM)</div>
                <div style={{ fontSize: '1.1rem', fontWeight: 800, margin: '6px 0' }}>
                  {(models.SVM?.home_win_prob * 100).toFixed(0)}% H
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  Total: {models.SVM?.predicted_total} pts
                </div>
              </div>

              {/* Neural Network Card */}
              <div style={{ background: 'rgba(0,0,0,0.3)', padding: '0.8rem', borderRadius: '12px', borderTop: '3px solid #145FD1' }}>
                <div style={{ fontSize: '0.8rem', fontWeight: 700, color: '#7DD3FC' }}>Red Neuronal (MLP)</div>
                <div style={{ fontSize: '1.1rem', fontWeight: 800, margin: '6px 0' }}>
                  {(models.NeuralNetwork?.home_win_prob * 100).toFixed(0)}% H
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  Total: {models.NeuralNetwork?.predicted_total} pts
                </div>
              </div>

              {/* Random Forest Card */}
              <div style={{ background: 'rgba(0,0,0,0.3)', padding: '0.8rem', borderRadius: '12px', borderTop: '3px solid #10b981' }}>
                <div style={{ fontSize: '0.8rem', fontWeight: 700, color: '#10b981' }}>Random Forest</div>
                <div style={{ fontSize: '1.1rem', fontWeight: 800, margin: '6px 0' }}>
                  {(models.RandomForest?.home_win_prob * 100).toFixed(0)}% H
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  Total: {models.RandomForest?.predicted_total} pts
                </div>
              </div>

              {/* XGBoost Card */}
              <div style={{ background: 'rgba(0,0,0,0.3)', padding: '0.8rem', borderRadius: '12px', borderTop: '3px solid #f97316' }}>
                <div style={{ fontSize: '0.8rem', fontWeight: 700, color: '#fb923c' }}>XGBoost</div>
                <div style={{ fontSize: '1.1rem', fontWeight: 800, margin: '6px 0' }}>
                  {(models.XGBoost?.home_win_prob * 100).toFixed(0)}% H
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  Total: {models.XGBoost?.predicted_total} pts
                </div>
              </div>

              {/* LightGBM Card */}
              <div style={{ background: 'rgba(0,0,0,0.3)', padding: '0.8rem', borderRadius: '12px', borderTop: '3px solid #eab308' }}>
                <div style={{ fontSize: '0.8rem', fontWeight: 700, color: '#facc15' }}>LightGBM</div>
                <div style={{ fontSize: '1.1rem', fontWeight: 800, margin: '6px 0' }}>
                  {(models.LightGBM?.home_win_prob * 100).toFixed(0)}% H
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  Total: {models.LightGBM?.predicted_total} pts
                </div>
              </div>
            </div>

            {/* Suggested Bets Table */}
            <div style={{ background: 'rgba(0,0,0,0.3)', borderRadius: '12px', padding: '1rem' }}>
              <h4 style={{ fontSize: '0.85rem', fontWeight: 700, marginBottom: '0.6rem' }}>Picks Recomendados para Líneas y Totales:</h4>
              <ul style={{ listStyle: 'none', display: 'grid', gap: '0.5rem', fontSize: '0.85rem' }}>
                <li style={{ display: 'flex', justifyContent: 'space-between', padding: '0.4rem 0', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Margen Estimado:</span>
                  <strong>{ens.predicted_margin > 0 ? `Ganará ${homeTeam} por +${ens.predicted_margin} pts` : `Ganará ${awayTeam} por +${Math.abs(ens.predicted_margin)} pts`}</strong>
                </li>
                <li style={{ display: 'flex', justifyContent: 'space-between', padding: '0.4rem 0', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Recomendación Handicap:</span>
                  <strong style={{ color: '#2F8FFF' }}>{ens.spread_pick}</strong>
                </li>
                <li style={{ display: 'flex', justifyContent: 'space-between', padding: '0.4rem 0' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Recomendación Over/Under:</span>
                  <strong style={{ color: '#10b981' }}>{ens.over_under_pick} (Proyección: {ens.predicted_total} pts)</strong>
                </li>
              </ul>
            </div>
          </div>
        ) : (
          <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
            Haz clic en "Ejecutar Inferencia ML" para generar las predicciones.
          </div>
        )}
      </div>
    </div>
  );
}
