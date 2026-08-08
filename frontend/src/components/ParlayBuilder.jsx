import React, { useState, useEffect } from 'react';
import { Layers, Trash2, DollarSign, Zap, CheckCircle, AlertTriangle } from 'lucide-react';
import { calculateParlay } from '../services/api';
import TeamIcon from './TeamIcon';

export default function ParlayBuilder({ parlayLegs, onRemoveLeg, onClearParlay }) {
  const [stake, setStake] = useState(50.0);
  const [parlayResult, setParlayResult] = useState(null);

  useEffect(() => {
    if (parlayLegs.length > 0) {
      calculateParlay(parlayLegs, Number(stake))
        .then(res => setParlayResult(res))
        .catch(err => console.error(err));
    } else {
      setParlayResult(null);
    }
  }, [parlayLegs, stake]);

  if (parlayLegs.length === 0) {
    return (
      <div className="glass-panel" style={{ padding: '3rem', textAlign: 'center' }}>
        <Layers size={48} color="var(--accent-cyan)" style={{ margin: '0 auto 1rem', opacity: 0.8 }} />
        <h3>Tu Combinada (Parlay) está vacía</h3>
        <p style={{ color: 'var(--text-muted)', marginTop: '0.5rem' }}>
          Explora la pestaña "Partidos 2026" y haz clic en "Agregar Pick a Parlay" para construir tu combinada con valor esperado (+EV).
        </p>
      </div>
    );
  }

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '1.5rem', alignItems: 'start' }}>
      {/* Selected Legs List */}
      <div className="glass-panel" style={{ padding: '1.5rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <h2 style={{ fontSize: '1.2rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Layers color="#00f2fe" size={22} /> Selecciones para la Combinada ({parlayLegs.length})
          </h2>
          <button onClick={onClearParlay} className="btn-secondary" style={{ padding: '0.4rem 0.8rem', fontSize: '0.8rem', color: '#ef4444' }}>
            <Trash2 size={14} /> Limpiar Todo
          </button>
        </div>

        <div style={{ display: 'grid', gap: '0.8rem' }}>
          {parlayLegs.map((leg, index) => (
            <div key={index} style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '12px', padding: '1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                <TeamIcon teamName={leg.pick === 'HOME' ? leg.home_team : leg.away_team} size={44} />
                <div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--accent-cyan)', fontWeight: 700 }}>{leg.league} • {leg.home_team} vs {leg.away_team}</div>
                  <div style={{ fontWeight: 700, fontSize: '0.95rem', marginTop: '2px' }}>Pick: {leg.pick_label}</div>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Prob. Algoritmo ML: {(leg.prob * 100).toFixed(1)}%</div>
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                <div className="mono" style={{ fontSize: '1.1rem', fontWeight: 800, color: 'var(--accent-gold)' }}>
                  @{leg.odds}
                </div>
                <button onClick={() => onRemoveLeg(leg.fixture_id)} style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', padding: '4px' }}>
                  <Trash2 size={18} />
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Parlay Odds & Payout Calculation */}
      <div className="glass-panel" style={{ padding: '1.5rem' }}>
        <h2 style={{ fontSize: '1.2rem', fontWeight: 700, marginBottom: '1.2rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <DollarSign color="#10b981" size={22} /> Resumen de la Combinada (Bet Slip)
        </h2>

        {parlayResult && (
          <div>
            {/* Value Recommendation Banner */}
            <div style={{
              background: parlayResult.parlay_ev_pct > 0 ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
              border: `1px solid ${parlayResult.parlay_ev_pct > 0 ? '#10b981' : '#ef4444'}`,
              borderRadius: '12px',
              padding: '0.8rem 1rem',
              marginBottom: '1.2rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.8rem'
            }}>
              {parlayResult.parlay_ev_pct > 0 ? <CheckCircle color="#10b981" size={24} /> : <AlertTriangle color="#ef4444" size={24} />}
              <div>
                <div style={{ fontWeight: 700, fontSize: '0.9rem', color: parlayResult.parlay_ev_pct > 0 ? '#10b981' : '#ef4444' }}>
                  {parlayResult.recommendation}
                </div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  EV Acumulado del Parlay: {parlayResult.parlay_ev_pct > 0 ? `+${parlayResult.parlay_ev_pct}%` : `${parlayResult.parlay_ev_pct}%`}
                </div>
              </div>
            </div>

            {/* Stake Input */}
            <div style={{ marginBottom: '1.2rem' }}>
              <label style={{ fontSize: '0.85rem', color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>Monto a Apostar ($ USD)</label>
              <input
                type="number"
                value={stake}
                onChange={e => setStake(Math.max(1, Number(e.target.value)))}
                style={{ width: '100%', fontSize: '1.1rem', fontWeight: 700 }}
              />
            </div>

            {/* Summary Metrics Grid */}
            <div style={{ background: 'rgba(0,0,0,0.3)', borderRadius: '12px', padding: '1rem', display: 'grid', gap: '0.8rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: '0.5rem' }}>
                <span style={{ color: 'var(--text-muted)' }}>Cuota Acumulada:</span>
                <strong className="mono" style={{ fontSize: '1.2rem', color: 'var(--accent-gold)' }}>@{parlayResult.combined_odds}</strong>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: '0.5rem' }}>
                <span style={{ color: 'var(--text-muted)' }}>Probabilidad Real Acumulada:</span>
                <strong style={{ color: '#00f2fe' }}>{parlayResult.win_probability_pct}%</strong>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: '0.5rem' }}>
                <span style={{ color: 'var(--text-muted)' }}>Ganancia Neta Estimada:</span>
                <strong style={{ color: '#10b981', fontSize: '1.1rem' }}>+${parlayResult.potential_profit}</strong>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', paddingTop: '0.2rem' }}>
                <span style={{ fontWeight: 700 }}>Pago Total Esperado:</span>
                <strong className="mono" style={{ fontSize: '1.3rem', color: '#ffffff' }}>${parlayResult.potential_payout}</strong>
              </div>
            </div>

            <button className="btn-primary" style={{ width: '100%', justifyContent: 'center', marginTop: '1.2rem', padding: '0.8rem' }}>
              <Zap size={18} /> Registrar Apuesta Parlay
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
