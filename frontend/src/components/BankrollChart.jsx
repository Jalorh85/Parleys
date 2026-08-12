import React, { useState, useEffect, useMemo } from 'react';
import { TrendingUp, TrendingDown, DollarSign, Percent, Target, Info } from 'lucide-react';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine
} from 'recharts';
import { fetchBankroll } from '../services/api';

const LEAGUES = [
  { value: '', label: 'Todas las ligas' },
  { value: 'LCUP', label: 'Leagues Cup' },
  { value: 'MLB', label: 'MLB' },
  { value: 'WNBA', label: 'WNBA' },
  { value: 'KBO', label: 'KBO' },
  { value: 'MX', label: 'Liga MX' },
  { value: 'NFL', label: 'NFL' },
];

const DAY_WINDOWS = [30, 60, 90, 180];

function pnlColor(value) {
  if (value == null) return 'var(--text-muted)';
  return value >= 0 ? '#10b981' : '#ef4444';
}

function formatMoney(value) {
  const sign = value < 0 ? '-' : '';
  return `${sign}$${Math.abs(value).toFixed(2)}`;
}

// "2026-07-21" -> "21/07"
function formatDateShort(dateStr) {
  const parts = (dateStr || '').split('-');
  if (parts.length !== 3) return dateStr;
  const [, m, d] = parts;
  return `${d}/${m}`;
}

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload || !payload.length) return null;
  const point = payload[0].payload;
  return (
    <div style={{
      background: 'rgba(15,17,26,0.95)',
      border: '1px solid rgba(255,255,255,0.15)',
      borderRadius: '10px',
      padding: '0.6rem 0.8rem',
      fontSize: '0.78rem',
      color: 'var(--text-main)',
      boxShadow: '0 8px 24px rgba(0,0,0,0.4)',
    }}>
      <div style={{ fontWeight: 700, marginBottom: '4px' }}>{formatDateShort(label)}</div>
      <div style={{ color: 'var(--text-muted)' }}>
        {point.bets} apuesta{point.bets === 1 ? '' : 's'} · {formatMoney(point.profit)} ese día
      </div>
      <div style={{ marginTop: '4px', fontWeight: 700, color: pnlColor(point.cumulative) }}>
        Acumulado: {formatMoney(point.cumulative)}
      </div>
    </div>
  );
}

function Stat({ label, value, color, icon: Icon }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
      {Icon && <Icon size={16} color={color} />}
      <div>
        <div style={{ fontSize: '1.05rem', fontWeight: 800, color }}>{value}</div>
        <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{label}</div>
      </div>
    </div>
  );
}

/**
 * Gráfica interactiva de evolución de bankroll acumulado.
 * Consume /api/bankroll (ver prediction_log.get_bankroll_simulation) --
 * usa EXCLUSIVAMENTE predicciones ya reconciliadas contra resultados
 * reales, nunca inventa nada. Selector de liga, ventana de días, stake
 * por apuesta, y toggle "solo picks +EV" vs "siempre el ganador predicho".
 */
export default function BankrollChart({ defaultLeague = '' }) {
  const [league, setLeague] = useState(defaultLeague);
  const [days, setDays] = useState(90);
  const [stake, setStake] = useState(10);
  const [onlyValueBets, setOnlyValueBets] = useState(true);

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    fetchBankroll(league || null, days, stake, onlyValueBets)
      .then(setData)
      .catch(err => setError(err.message || 'Error al cargar la simulación de bankroll'))
      .finally(() => setLoading(false));
  }, [league, days, stake, onlyValueBets]);

  const chartData = useMemo(() => (data && data.series) || [], [data]);
  const hasData = chartData.length > 0;
  const accentColor = data && data.net_profit >= 0 ? '#10b981' : '#ef4444';

  return (
    <div className="glass-panel" style={{ padding: '1.2rem', marginBottom: '1rem' }}>
      {/* Header */}
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start',
        flexWrap: 'wrap', gap: '0.75rem', marginBottom: '1rem'
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <DollarSign size={20} color="#00f2fe" />
            <h3 style={{ margin: 0, fontSize: '1.05rem', fontWeight: 800, color: 'var(--text-main)' }}>
              Evolución de Bankroll
            </h3>
          </div>
          <p style={{ margin: '2px 0 0 28px', fontSize: '0.76rem', color: 'var(--text-muted)' }}>
            Simulación retrospectiva con resultados reales ya reconciliados — no es una recomendación de apuesta.
          </p>
        </div>

        {/* Toggle: Value Bets vs Ganador predicho */}
        <div style={{ display: 'flex', gap: '0.4rem' }}>
          <button
            onClick={() => setOnlyValueBets(true)}
            className={onlyValueBets ? 'btn-primary' : 'btn-secondary'}
            style={{ fontSize: '0.76rem', padding: '0.35rem 0.8rem' }}
          >
            Solo +EV
          </button>
          <button
            onClick={() => setOnlyValueBets(false)}
            className={!onlyValueBets ? 'btn-primary' : 'btn-secondary'}
            style={{ fontSize: '0.76rem', padding: '0.35rem 0.8rem' }}
          >
            Ganador predicho
          </button>
        </div>
      </div>

      {/* Controles: liga, ventana de días, stake */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap', marginBottom: '1rem' }}>
        <select
          value={league}
          onChange={e => setLeague(e.target.value)}
          style={{
            background: 'rgba(255,255,255,0.07)',
            border: '1px solid rgba(255,255,255,0.15)',
            borderRadius: '8px',
            color: 'var(--text-main)',
            padding: '0.4rem 0.75rem',
            fontSize: '0.8rem',
            cursor: 'pointer',
          }}
        >
          {LEAGUES.map(l => (
            <option key={l.value} value={l.value}>{l.label}</option>
          ))}
        </select>

        {DAY_WINDOWS.map(w => (
          <button
            key={w}
            onClick={() => setDays(w)}
            className={days === w ? 'btn-primary' : 'btn-secondary'}
            style={{ fontSize: '0.78rem', padding: '0.4rem 0.9rem' }}
          >
            {w}d
          </button>
        ))}

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginLeft: 'auto' }}>
          <label style={{ fontSize: '0.76rem', color: 'var(--text-muted)' }}>Stake/apuesta</label>
          <input
            type="number"
            min={1}
            step={1}
            value={stake}
            onChange={e => setStake(Math.max(1, Number(e.target.value) || 1))}
            style={{
              width: '64px',
              background: 'rgba(255,255,255,0.07)',
              border: '1px solid rgba(255,255,255,0.15)',
              borderRadius: '8px',
              color: 'var(--text-main)',
              padding: '0.35rem 0.5rem',
              fontSize: '0.8rem',
            }}
          />
        </div>
      </div>

      {/* Loading */}
      {loading && (
        <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
          Calculando simulación...
        </div>
      )}

      {/* Error */}
      {!loading && error && (
        <div style={{ padding: '1.5rem', textAlign: 'center', color: '#ef4444', fontSize: '0.85rem' }}>
          {error}
        </div>
      )}

      {/* Empty state */}
      {!loading && !error && !hasData && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '1.5rem',
          color: 'var(--text-muted)', fontSize: '0.82rem'
        }}>
          <Info size={16} />
          Todavía no hay picks resueltos en esta ventana — vuelve en uno o dos días, o prueba una ventana más amplia.
        </div>
      )}

      {/* Chart + stats */}
      {!loading && !error && hasData && (
        <>
          {/* Stats row */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1.2rem', marginBottom: '1rem' }}>
            <Stat
              label="Profit neto"
              value={formatMoney(data.net_profit)}
              color={pnlColor(data.net_profit)}
              icon={data.net_profit >= 0 ? TrendingUp : TrendingDown}
            />
            <Stat
              label="ROI"
              value={data.roi_pct != null ? `${data.roi_pct}%` : '—'}
              color={pnlColor(data.roi_pct)}
              icon={Percent}
            />
            <Stat
              label="Win rate"
              value={data.win_rate_pct != null ? `${data.win_rate_pct}%` : '—'}
              color="var(--text-main)"
              icon={Target}
            />
            <Stat
              label="Apuestas"
              value={`${data.total_bets} (${data.wins}W-${data.losses}L)`}
              color="var(--text-main)"
            />
          </div>

          {/* Chart */}
          <div style={{ width: '100%', height: 260 }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} margin={{ top: 8, right: 8, left: -12, bottom: 0 }}>
                <defs>
                  <linearGradient id="bankrollFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={accentColor} stopOpacity={0.35} />
                    <stop offset="100%" stopColor={accentColor} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" vertical={false} />
                <XAxis
                  dataKey="date"
                  tickFormatter={formatDateShort}
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
                  width={56}
                />
                <ReferenceLine y={0} stroke="rgba(255,255,255,0.25)" strokeDasharray="4 4" />
                <Tooltip content={<CustomTooltip />} />
                <Area
                  type="monotone"
                  dataKey="cumulative"
                  stroke={accentColor}
                  strokeWidth={2.5}
                  fill="url(#bankrollFill)"
                  dot={false}
                  activeDot={{ r: 4, fill: accentColor, stroke: '#0f111a', strokeWidth: 2 }}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </>
      )}
    </div>
  );
}
