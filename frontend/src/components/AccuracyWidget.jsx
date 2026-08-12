import React, { useState, useEffect, useMemo } from 'react';
import { Target, Zap, Info } from 'lucide-react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine
} from 'recharts';
import { fetchAccuracy } from '../services/api';

// Color según qué tan lejos está el % de acierto de "moneda al aire" (50%)
function accuracyColor(pct) {
  if (pct == null) return 'var(--text-muted)';
  if (pct >= 55) return '#10b981';
  if (pct >= 48) return '#f5a623';
  return '#ef4444';
}

// Paleta fija por liga -- misma idea que Header.jsx, para que el color de
// cada línea sea siempre reconocible entre vistas.
const LEAGUE_COLORS = {
  LCUP: '#2F8FFF',
  MLB: '#ef4444',
  WNBA: '#f5a623',
  KBO: '#10b981',
  MX: '#a855f7',
  NFL: '#00f2fe',
};
const FALLBACK_COLORS = ['#2F8FFF', '#ef4444', '#f5a623', '#10b981', '#a855f7', '#00f2fe', '#f472b6', '#94a3b8'];
function colorForLeague(lg, idx) {
  return LEAGUE_COLORS[lg] || FALLBACK_COLORS[idx % FALLBACK_COLORS.length];
}

// "2026-07-21" -> "21/07"
function formatDateShort(dateStr) {
  const parts = (dateStr || '').split('-');
  if (parts.length !== 3) return dateStr;
  const [, m, d] = parts;
  return `${d}/${m}`;
}

// El endpoint /api/accuracy entrega `per_league` con los totales agregados
// por liga. Si además trae un desglose diario por liga (`per_league[lg].daily`,
// con la misma forma que `daily` general), lo usamos para dibujar una línea
// por liga superpuesta. Si el backend todavía no manda ese desglose, esta
// función devuelve una lista vacía y el widget cae de vuelta al trend
// agregado (ver `overallSeries` más abajo) -- así el componente no se rompe
// mientras se agrega soporte del lado del servidor.
function buildLeagueSeries(per_league) {
  const leaguesWithDaily = Object.entries(per_league || {})
    .filter(([, v]) => Array.isArray(v.daily) && v.daily.length > 0);

  if (!leaguesWithDaily.length) return { series: [], leagueKeys: [] };

  const dateMap = new Map();
  leaguesWithDaily.forEach(([lg, v]) => {
    v.daily.forEach(d => {
      if (!dateMap.has(d.date)) dateMap.set(d.date, { date: d.date });
      dateMap.get(d.date)[lg] = d.accuracy_pct;
      dateMap.get(d.date)[`${lg}__resolved`] = d.resolved;
    });
  });

  const series = Array.from(dateMap.values()).sort((a, b) => a.date.localeCompare(b.date));
  return { series, leagueKeys: leaguesWithDaily.map(([lg]) => lg) };
}

function CustomTooltip({ active, payload, label, leagueKeys }) {
  if (!active || !payload || !payload.length) return null;
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
      {payload
        .filter(p => leagueKeys.includes(p.dataKey))
        .sort((a, b) => (b.value || 0) - (a.value || 0))
        .map(p => {
          const point = p.payload || {};
          const resolved = point[`${p.dataKey}__resolved`];
          return (
            <div key={p.dataKey} style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', marginTop: '2px' }}>
              <span style={{ color: p.color, fontWeight: 600 }}>{p.dataKey}</span>
              <span style={{ color: 'var(--text-muted)' }}>
                {p.value != null ? `${p.value}%` : '—'}{resolved != null ? ` (${resolved})` : ''}
              </span>
            </div>
          );
        })}
    </div>
  );
}

function CustomLegend({ leagueKeys, hidden, onToggle }) {
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '0.6rem' }}>
      {leagueKeys.map((lg, i) => {
        const isHidden = hidden.has(lg);
        const color = colorForLeague(lg, i);
        return (
          <button
            key={lg}
            onClick={() => onToggle(lg)}
            className="badge"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.35rem',
              background: isHidden ? 'rgba(255,255,255,0.03)' : `${color}1a`,
              border: `1px solid ${isHidden ? 'rgba(255,255,255,0.1)' : `${color}55`}`,
              color: isHidden ? 'var(--text-muted)' : color,
              fontSize: '0.72rem',
              cursor: 'pointer',
              opacity: isHidden ? 0.5 : 1,
              transition: 'all 0.15s ease',
            }}
          >
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: color, display: 'inline-block' }} />
            {lg}
          </button>
        );
      })}
    </div>
  );
}

export default function AccuracyWidget({ activeLeague }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [hiddenLeagues, setHiddenLeagues] = useState(() => new Set());

  useEffect(() => {
    setLoading(true);
    setError(null);
    fetchAccuracy(null, 30)
      .then(setData)
      .catch(err => setError(err.message || 'Error al cargar precisión real'))
      .finally(() => setLoading(false));
  }, []);

  const { series: leagueSeries, leagueKeys } = useMemo(
    () => buildLeagueSeries(data && data.per_league),
    [data]
  );

  const toggleLeague = (lg) => {
    setHiddenLeagues(prev => {
      const next = new Set(prev);
      if (next.has(lg)) next.delete(lg); else next.add(lg);
      return next;
    });
  };

  if (loading) {
    return (
      <div className="glass-panel" style={{ padding: '1rem 1.2rem', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
        <Zap className="pulse-glow" size={18} color="#2F8FFF" />
        <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Calculando precisión real...</span>
      </div>
    );
  }

  if (error || !data) {
    return null; // el widget es un extra -- si falla, no debe ensuciar el dashboard principal
  }

  const { overall, per_league, daily, days } = data;

  if (!overall.resolved_predictions) {
    return (
      <div className="glass-panel" style={{ padding: '1rem 1.2rem', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
        <Info size={18} color="var(--text-muted)" />
        <span style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
          Todavía no hay predicciones reconciliadas contra resultados reales — vuelve en uno o dos días para ver la precisión real del modelo.
        </span>
      </div>
    );
  }

  const leaguesWithData = Object.entries(per_league).filter(([, v]) => v.resolved_predictions > 0);

  // Serie agregada (todas las ligas juntas), usada como fallback si el
  // backend todavía no manda desglose diario por liga.
  const overallSeries = (daily || []).slice(-30);
  const hasLeagueBreakdown = leagueKeys.length > 1 && leagueSeries.length > 1;
  const chartSeries = hasLeagueBreakdown ? leagueSeries : overallSeries;
  const showChart = chartSeries.length > 1;

  return (
    <div className="glass-panel" style={{ padding: '1.2rem', marginBottom: '1rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem', marginBottom: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.7rem' }}>
          <Target size={22} color={accuracyColor(overall.winner_accuracy_pct)} />
          <div>
            <div style={{ fontSize: '1.4rem', fontWeight: 800, color: accuracyColor(overall.winner_accuracy_pct) }}>
              {overall.winner_accuracy_pct != null ? `${overall.winner_accuracy_pct}%` : '—'}
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Precisión real (ganador) · últimos {days} días · {overall.resolved_predictions} partidos resueltos
            </div>
          </div>
        </div>

        {overall.ou_resolved > 0 && (
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: '1.1rem', fontWeight: 700, color: accuracyColor(overall.ou_accuracy_pct) }}>
              {overall.ou_accuracy_pct}%
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Over/Under · {overall.ou_resolved} picks con valor
            </div>
          </div>
        )}
      </div>

      {/* Desglose por liga (totales) */}
      {leaguesWithData.length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginBottom: showChart ? '1rem' : 0 }}>
          {leaguesWithData.map(([lg, v]) => (
            <span
              key={lg}
              className="badge"
              style={{
                background: 'rgba(255,255,255,0.04)',
                border: `1px solid ${accuracyColor(v.winner_accuracy_pct)}40`,
                color: accuracyColor(v.winner_accuracy_pct),
                fontSize: '0.75rem',
              }}
              title={`${v.resolved_predictions} partidos resueltos`}
            >
              {lg}: {v.winner_accuracy_pct}% ({v.resolved_predictions})
            </span>
          ))}
        </div>
      )}

      {/* Tendencia diaria interactiva */}
      {showChart && (
        <div>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>
            {hasLeagueBreakdown ? 'Tendencia diaria por liga' : 'Tendencia diaria (todas las ligas)'}
          </div>

          {hasLeagueBreakdown && (
            <CustomLegend leagueKeys={leagueKeys} hidden={hiddenLeagues} onToggle={toggleLeague} />
          )}

          <div style={{ width: '100%', height: 200 }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartSeries} margin={{ top: 4, right: 8, left: -18, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" vertical={false} />
                <XAxis
                  dataKey="date"
                  tickFormatter={formatDateShort}
                  tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
                  axisLine={{ stroke: 'rgba(255,255,255,0.1)' }}
                  tickLine={false}
                  minTickGap={20}
                />
                <YAxis
                  domain={[0, 100]}
                  tickFormatter={v => `${v}%`}
                  tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                  width={40}
                />
                <ReferenceLine y={50} stroke="rgba(255,255,255,0.25)" strokeDasharray="4 4" />
                <Tooltip
                  content={<CustomTooltip leagueKeys={hasLeagueBreakdown ? leagueKeys : ['accuracy_pct']} />}
                  cursor={{ stroke: 'rgba(255,255,255,0.15)' }}
                />

                {hasLeagueBreakdown ? (
                  leagueKeys.map((lg, i) => (
                    <Line
                      key={lg}
                      type="monotone"
                      dataKey={lg}
                      name={lg}
                      stroke={colorForLeague(lg, i)}
                      strokeWidth={2}
                      dot={false}
                      activeDot={{ r: 4, strokeWidth: 2, stroke: '#0f111a' }}
                      hide={hiddenLeagues.has(lg)}
                      connectNulls
                    />
                  ))
                ) : (
                  <Line
                    type="monotone"
                    dataKey="accuracy_pct"
                    name="Precisión"
                    stroke="#2F8FFF"
                    strokeWidth={2}
                    dot={false}
                    activeDot={{ r: 4, strokeWidth: 2, stroke: '#0f111a' }}
                    connectNulls
                  />
                )}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  );
}
