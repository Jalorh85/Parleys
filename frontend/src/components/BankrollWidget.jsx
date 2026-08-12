import React, { useState, useEffect } from 'react';
import { Wallet, Zap, Info } from 'lucide-react';
import { fetchBankroll } from '../services/api';

function profitColor(value) {
  if (value == null) return 'var(--text-muted)';
  return value >= 0 ? '#10b981' : '#ef4444';
}

// Genera un path SVG simple a partir de la serie acumulada
function buildSparklinePath(series, width, height) {
  if (!series || series.length < 2) return '';
  const values = series.map(s => s.cumulative);
  const min = Math.min(0, ...values);
  const max = Math.max(0, ...values);
  const range = max - min || 1;
  const stepX = width / (series.length - 1);

  return series
    .map((s, i) => {
      const x = i * stepX;
      const y = height - ((s.cumulative - min) / range) * height;
      return `${i === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${y.toFixed(1)}`;
    })
    .join(' ');
}

export default function BankrollWidget() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [onlyValueBets, setOnlyValueBets] = useState(true);

  useEffect(() => {
    setLoading(true);
    setError(null);
    fetchBankroll(null, 90, 10, onlyValueBets)
      .then(setData)
      .catch(err => setError(err.message || 'Error al cargar la simulación'))
      .finally(() => setLoading(false));
  }, [onlyValueBets]);

  if (loading) {
    return (
      <div className="glass-panel" style={{ padding: '1rem 1.2rem', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
        <Zap className="pulse-glow" size={18} color="#2F8FFF" />
        <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Calculando simulación de bankroll...</span>
      </div>
    );
  }

  if (error || !data) return null; // widget extra -- si falla, no ensucia el dashboard

  if (!data.total_bets) {
    return (
      <div className="glass-panel" style={{ padding: '1rem 1.2rem', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
        <Info size={18} color="var(--text-muted)" />
        <span style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
          Todavía no hay suficientes predicciones {onlyValueBets ? '+EV ' : ''}reconciliadas para simular un historial de apuestas.
        </span>
      </div>
    );
  }

  const width = 600;
  const height = 60;
  const path = buildSparklinePath(data.series, width, height);
  const strokeColor = profitColor(data.net_profit);

  return (
    <div className="glass-panel" style={{ padding: '1.2rem', marginBottom: '1rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem', marginBottom: '0.8rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.7rem' }}>
          <Wallet size={22} color={strokeColor} />
          <div>
            <div style={{ fontSize: '1.4rem', fontWeight: 800, color: strokeColor }}>
              {data.net_profit >= 0 ? '+' : ''}${data.net_profit.toFixed(2)}
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Bankroll simulado · últimos {data.days} días · ${data.stake_per_bet} por apuesta · {data.total_bets} apuestas
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          <button
            onClick={() => setOnlyValueBets(true)}
            className={onlyValueBets ? 'btn-primary' : 'btn-secondary'}
            style={{ fontSize: '0.72rem', padding: '0.3rem 0.6rem' }}
          >
            Solo +EV
          </button>
          <button
            onClick={() => setOnlyValueBets(false)}
            className={!onlyValueBets ? 'btn-primary' : 'btn-secondary'}
            style={{ fontSize: '0.72rem', padding: '0.3rem 0.6rem' }}
          >
            Siempre el favorito del modelo
          </button>
        </div>
      </div>

      <div style={{ display: 'flex', gap: '1.5rem', fontSize: '0.78rem', marginBottom: '0.8rem', flexWrap: 'wrap' }}>
        <span><span style={{ color: 'var(--text-muted)' }}>Aciertos:</span> <strong>{data.wins}/{data.total_bets}</strong> ({data.win_rate_pct}%)</span>
        <span><span style={{ color: 'var(--text-muted)' }}>Total apostado:</span> <strong>${data.total_staked.toFixed(2)}</strong></span>
        <span><span style={{ color: 'var(--text-muted)' }}>ROI:</span> <strong style={{ color: profitColor(data.roi_pct) }}>{data.roi_pct >= 0 ? '+' : ''}{data.roi_pct}%</strong></span>
      </div>

      {path && (
        <svg viewBox={`0 0 ${width} ${height}`} style={{ width: '100%', height: `${height}px`, display: 'block' }} preserveAspectRatio="none">
          <line x1="0" y1={height / 2} x2={width} y2={height / 2} stroke="rgba(255,255,255,0.08)" strokeWidth="1" />
          <path d={path} fill="none" stroke={strokeColor} strokeWidth="2" />
        </svg>
      )}

      <p style={{ fontSize: '0.68rem', color: 'var(--text-dim, var(--text-muted))', marginTop: '0.6rem', marginBottom: 0 }}>
        Simulación retrospectiva con resultados reales ya confirmados — no es una recomendación de apuesta ni garantiza resultados futuros.
      </p>
    </div>
  );
}
