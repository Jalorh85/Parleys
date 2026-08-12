import React, { useState, useEffect, useMemo } from 'react';
import { TrendingUp, DollarSign, Play, Activity } from 'lucide-react';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine
} from 'recharts';
import { runBacktest } from '../services/api';

function formatMoney(value) {
  const sign = value < 0 ? '-' : '';
  return `${sign}$${Math.abs(value).toFixed(2)}`;
}

function BankrollTooltip({ active, payload, startBankroll }) {
  if (!active || !payload || !payload.length) return null;
  const point = payload[0].payload;
  const delta = point.bankroll - startBankroll;
  return (
    <div style={{
      background: 'rgba(15,17,26,0.95)',
      border: '1px solid rgba(255,255,255,0.15)',
      borderRadius: '10px',
      padding: '0.6rem 0.8rem',
      fontSize: '0.78rem',
      color: '#ffffff',
      boxShadow: '0 8px 24px rgba(0,0,0,0.4)',
    }}>
      <div style={{ fontWeight: 700, marginBottom: '4px' }}>
        {point.bet === 0 ? 'Capital inicial' : `Apuesta #${point.bet}`}
      </div>
      <div style={{ color: 'var(--text-muted)' }}>{formatMoney(point.bankroll)}</div>
      <div style={{ marginTop: '2px', fontWeight: 700, color: delta >= 0 ? '#10b981' : '#ef4444' }}>
        {delta >= 0 ? '+' : ''}{formatMoney(delta)} vs. inicial
      </div>
    </div>
  );
}

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

  const chartData = useMemo(() => {
    if (!progression.length) return [];
    const start = res.initial_bankroll ?? Number(initialBankroll);
    return [
      { bet: 0, bankroll: start },
      ...progression.map((val, idx) => ({ bet: idx + 1, bankroll: val })),
    ];
  }, [progression, res.initial_bankroll, initialBankroll]);

  const startBankroll = res.initial_bankroll ?? Number(initialBankroll);
  const accentColor = res.net_profit >= 0 ? '#10b981' : '#ef4444';

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

            {/* Bankroll Progression Chart */}
            <div style={{ background: 'rgba(0,0,0,0.4)', borderRadius: '12px', padding: '1rem', marginBottom: '1.2rem' }}>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '8px' }}>Evolución del Capital (Bankroll Growth):</div>
              <div style={{ width: '100%', height: 180 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={chartData} margin={{ top: 8, right: 8, left: -12, bottom: 0 }}>
                    <defs>
                      <linearGradient id="backtestFill" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor={accentColor} stopOpacity={0.35} />
                        <stop offset="100%" stopColor={accentColor} stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" vertical={false} />
                    <XAxis
                      dataKey="bet"
                      tickFormatter={v => v === 0 ? 'Inicio' : `#${v}`}
                      tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
                      axisLine={{ stroke: 'rgba(255,255,255,0.1)' }}
                      tickLine={false}
                      minTickGap={24}
                    />
                    <YAxis
                      tickFormatter={v => `$${v}`}
                      tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
                      axisLine={false}
                      tickLine={false}
                      width={52}
                    />
                    <ReferenceLine y={startBankroll} stroke="rgba(255,255,255,0.25)" strokeDasharray="4 4" />
                    <Tooltip content={<BankrollTooltip startBankroll={startBankroll} />} cursor={{ stroke: 'rgba(255,255,255,0.15)' }} />
                    <Area
                      type="monotone"
                      dataKey="bankroll"
                      stroke={accentColor}
                      strokeWidth={2.5}
                      fill="url(#backtestFill)"
                      dot={false}
                      activeDot={{ r: 4, fill: accentColor, stroke: '#0f111a', strokeWidth: 2 }}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
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
