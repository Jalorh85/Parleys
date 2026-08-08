import React, { useState, useEffect } from 'react';
import { TrendingUp, DollarSign, Play, Activity } from 'lucide-react';
import { runBacktest } from '../services/api';

export default function BacktestSimulator({ activeLeague }) {
  const [initialBankroll, setInitialBankroll] = useState(1000);
  const [stakingStrategy, setStakingStrategy] = useState('kelly');
  const [flatStakePct, setFlatStakePct] = useState(0.03);
  const [minEvPct, setMinEvPct] = useState(2.0);
  const [minConfidence, setMinConfidence] = useState(10.0);

  const [backtestData, setBacktestData] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleExecuteBacktest = async () => {
    setLoading(true);
    try {
      const payload = {
        league: activeLeague,
        initial_bankroll: Number(initialBankroll),
        staking_strategy: stakingStrategy,
        flat_stake_pct: Number(flatStakePct),
        min_ev_pct: Number(minEvPct),
        min_confidence: Number(minConfidence)
      };
      const res = await runBacktest(payload);
      setBacktestData(res.result);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    handleExecuteBacktest();
  }, [activeLeague]);

  const res = backtestData || {};
  const progression = res.bankroll_progression || [];

  // Calculate SVG line points for bankroll chart
  const maxB = Math.max(...progression, initialBankroll * 1.5);
  const minB = Math.min(...progression, initialBankroll * 0.7);
  const pointsStr = progression.map((val, idx) => {
    const x = (idx / (progression.length - 1 || 1)) * 500;
    const y = 150 - ((val - minB) / (maxB - minB || 1)) * 130;
    return `${x},${y}`;
  }).join(' ');

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.3fr', gap: '1.5rem', alignItems: 'start' }}>
      {/* Strategy Config Form */}
      <div className="glass-panel" style={{ padding: '1.5rem' }}>
        <h2 style={{ fontSize: '1.2rem', fontWeight: 700, marginBottom: '1.2rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <TrendingUp color="#10b981" size={22} /> Parámetros del Simulador de ROI
        </h2>

        {/* Initial Capital */}
        <div style={{ marginBottom: '1rem' }}>
          <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>Bankroll Inicial ($ USD)</label>
          <input type="number" value={initialBankroll} onChange={e => setInitialBankroll(e.target.value)} style={{ width: '100%' }} />
        </div>

        {/* Strategy Selector */}
        <div style={{ marginBottom: '1rem' }}>
          <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>Estrategia de Gestió de Gestión de Capital</label>
          <select value={stakingStrategy} onChange={e => setStakingStrategy(e.target.value)} style={{ width: '100%' }}>
            <option value="kelly">Criterio de Kelly Fraccionado (Recomendado)</option>
            <option value="flat">Staking Plano (Flat Bet)</option>
          </select>
        </div>

        {stakingStrategy === 'flat' && (
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>% de Capital por Apuesta (Flat Stake)</label>
            <input type="number" step="0.01" value={flatStakePct} onChange={e => setFlatStakePct(e.target.value)} style={{ width: '100%' }} />
          </div>
        )}

        {/* Minimum EV filter */}
        <div style={{ marginBottom: '1.2rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: '4px' }}>
            <span>Filtro Mínimo de Valor +EV:</span>
            <strong>+{minEvPct}% EV</strong>
          </div>
          <input type="range" min="0" max="10" step="0.5" value={minEvPct} onChange={e => setMinEvPct(e.target.value)} style={{ width: '100%' }} />
        </div>

        <button onClick={handleExecuteBacktest} className="btn-primary" style={{ width: '100%', justifyContent: 'center' }} disabled={loading}>
          <Play size={18} /> {loading ? 'Simulando...' : 'Ejecutar Simulación Backtest'}
        </button>
      </div>

      {/* Backtest Results & Chart */}
      <div className="glass-panel" style={{ padding: '1.5rem' }}>
        <h2 style={{ fontSize: '1.2rem', fontWeight: 700, marginBottom: '1.2rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Activity color="#00f2fe" size={22} /> Desempeño Histórico de Apuestas ({activeLeague})
        </h2>

        {backtestData ? (
          <div>
            {/* Key Metrics KPI Cards */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.8rem', marginBottom: '1.2rem' }}>
              <div style={{ background: 'rgba(0,0,0,0.3)', padding: '0.8rem', borderRadius: '12px', textAlign: 'center' }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Ganancia Neta</span>
                <div style={{ fontSize: '1.2rem', fontWeight: 800, color: res.net_profit >= 0 ? '#10b981' : '#ef4444', marginTop: '2px' }}>
                  {res.net_profit >= 0 ? `+$${res.net_profit}` : `-$${Math.abs(res.net_profit)}`}
                </div>
              </div>

              <div style={{ background: 'rgba(0,0,0,0.3)', padding: '0.8rem', borderRadius: '12px', textAlign: 'center' }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>ROI Yield %</span>
                <div style={{ fontSize: '1.2rem', fontWeight: 800, color: res.roi_pct >= 0 ? '#10b981' : '#ef4444', marginTop: '2px' }}>
                  {res.roi_pct >= 0 ? `+${res.roi_pct}%` : `${res.roi_pct}%`}
                </div>
              </div>

              <div style={{ background: 'rgba(0,0,0,0.3)', padding: '0.8rem', borderRadius: '12px', textAlign: 'center' }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Win Rate ({res.winning_bets}/{res.total_bets})</span>
                <div style={{ fontSize: '1.2rem', fontWeight: 800, color: '#00f2fe', marginTop: '2px' }}>
                  {res.win_rate}%
                </div>
              </div>
            </div>

            {/* Bankroll Progression SVG Chart */}
            <div style={{ background: 'rgba(0,0,0,0.4)', borderRadius: '12px', padding: '1rem', marginBottom: '1.2rem' }}>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '8px' }}>Evolución del Capital (Bankroll Growth):</div>
              <svg viewBox="0 0 500 160" style={{ width: '100%', height: '140px', overflow: 'visible' }}>
                <polyline
                  fill="none"
                  stroke="#10b981"
                  strokeWidth="3"
                  points={pointsStr}
                />
              </svg>
            </div>

            {/* Recent Trades Table */}
            <h4 style={{ fontSize: '0.85rem', fontWeight: 700, marginBottom: '0.6rem' }}>Últimas Operaciones Ejecutadas:</h4>
            <div style={{ overflowX: 'auto', maxHeight: '180px' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
                <thead>
                  <tr style={{ color: 'var(--text-muted)', borderBottom: '1px solid rgba(255,255,255,0.08)' }}>
                    <th style={{ padding: '4px' }}>Partido</th>
                    <th style={{ padding: '4px' }}>Pick</th>
                    <th style={{ padding: '4px' }}>Cuota</th>
                    <th style={{ padding: '4px' }}>Resultado</th>
                  </tr>
                </thead>
                <tbody>
                  {(res.recent_trades || []).map((tr, idx) => (
                    <tr key={idx} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                      <td style={{ padding: '4px' }}>{tr.game}</td>
                      <td style={{ padding: '4px', fontWeight: 700, color: '#00f2fe' }}>{tr.pick}</td>
                      <td className="mono" style={{ padding: '4px' }}>@{tr.odds}</td>
                      <td style={{ padding: '4px', fontWeight: 700, color: tr.won ? '#10b981' : '#ef4444' }}>
                        {tr.won ? `+$${tr.profit}` : `-$${Math.abs(tr.profit)}`}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          <div>Haz clic en "Ejecutar Simulación Backtest"</div>
        )}
      </div>
    </div>
  );
}
