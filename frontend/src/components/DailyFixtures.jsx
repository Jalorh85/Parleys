import React, { useState, useMemo } from 'react';
import { ShieldAlert, Zap, TrendingUp, WifiOff, RefreshCw, CalendarX, SlidersHorizontal, ArrowUpDown, Scale, ChevronDown, ChevronUp, Lightbulb } from 'lucide-react';
import TeamIcon from './TeamIcon';

// Convierte home_win_prob a texto "%","—" si el modelo no vino en la respuesta
// (evita el "NaN%" cuando fix.prediction o un modelo puntual no existen)
const modelPct = (model) =>
  model?.home_win_prob != null ? `${(model.home_win_prob * 100).toFixed(0)}%` : '—';

export default function DailyFixtures({ fixtures, loading, error, selectedDate, onRetry, noDataMessage }) {
  // Hooks SIEMPRE arriba de cualquier `return` condicional (loading/error/
  // vacío) -- si no, React pierde el orden de hooks entre renders.
  const [filterMode, setFilterMode] = useState('all'); // 'all' | 'ev' | 'confidence'
  const [sortMode, setSortMode] = useState('time'); // 'time' | 'confidence'
  const [expandedExplanations, setExpandedExplanations] = useState({}); // fixture_id -> bool

  const toggleExplanation = (fixtureId) => {
    setExpandedExplanations(prev => ({ ...prev, [fixtureId]: !prev[fixtureId] }));
  };

  const visibleFixtures = useMemo(() => {
    if (!fixtures || fixtures.length === 0) return [];
    let list = [...fixtures];

    if (filterMode === 'ev') {
      list = list.filter(f => (f.prediction?.ensemble?.value_ev_pct ?? 0) > 0);
    } else if (filterMode === 'confidence') {
      list = list.filter(f => (f.prediction?.ensemble?.confidence ?? 0) >= 65);
    }

    if (sortMode === 'confidence') {
      list.sort((a, b) => (b.prediction?.ensemble?.confidence ?? -1) - (a.prediction?.ensemble?.confidence ?? -1));
    } else {
      list.sort((a, b) => (a.time || '').localeCompare(b.time || ''));
    }

    return list;
  }, [fixtures, filterMode, sortMode]);

  if (loading) {
    return (
      <div className="glass-panel" style={{ padding: '3rem', textAlign: 'center' }}>
        <Zap className="pulse-glow" size={48} color="#2F8FFF" style={{ margin: '0 auto 1rem' }} />
        <h3>Ejecutando Modelos SVM & Redes Neuronales...</h3>
        <p style={{ color: 'var(--text-muted)' }}>Cargando partidos para {selectedDate || 'mañana'}</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="glass-panel" style={{ padding: '3rem', textAlign: 'center' }}>
        <WifiOff size={48} color="#ff4d4d" style={{ margin: '0 auto 1rem' }} />
        <h3>Error de Conexión</h3>
        <p style={{ color: 'var(--text-muted)', marginBottom: '1.5rem' }}>No pudimos conectar con el servidor de predicciones.</p>
        <button onClick={onRetry} className="btn-primary" style={{ margin: '0 auto' }}>
          <RefreshCw size={16} /> Intentar de nuevo
        </button>
      </div>
    );
  }

  if (!fixtures || fixtures.length === 0) {
    // El backend ya no rellena con partidos simulados cuando no hay reales —
    // manda `message` en la respuesta de /api/fixtures (ver main.py). Si el
    // componente padre todavía no reenvía ese campo como `noDataMessage`,
    // se arma acá un mensaje equivalente con la fecha seleccionada.
    const fallbackMessage = `No hay partidos reales para la fecha del ${selectedDate || 'día de hoy'}. Revisa el calendario para consultar los partidos en otra fecha.`;

    return (
      <div className="glass-panel" style={{ padding: '3rem', textAlign: 'center' }}>
        <CalendarX size={48} color="#f5a623" style={{ margin: '0 auto 1rem' }} />
        <h3 style={{ marginBottom: '0.5rem' }}>Sin Partidos Reales Disponibles</h3>
        <p style={{ color: 'var(--text-muted)', maxWidth: '440px', margin: '0 auto' }}>
          {noDataMessage || fallbackMessage}
        </p>
      </div>
    );
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.8rem' }}>
        <div>
          <h2 style={{ fontSize: '1.3rem', fontWeight: 700 }}>
            Partidos de la Temporada 2026 & Pronósticos ML
          </h2>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
            Predicciones calculadas mediante XGBoost + LightGBM + SVM + Redes Neuronales + Meta-Ensemble + Random Forest
          </p>
        </div>
        <span className="badge badge-ev">
          <TrendingUp size={14} style={{ display: 'inline', marginRight: '4px' }} />
          Detección de Valor +EV Activa
        </span>
      </div>

      {/* Controles de filtro/orden */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap',
        marginBottom: '1.2rem', padding: '0.6rem 0.8rem',
        background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '10px',
      }}>
        <SlidersHorizontal size={15} color="var(--text-muted)" />
        {[
          { key: 'all', label: 'Todos' },
          { key: 'ev', label: '+EV' },
          { key: 'confidence', label: 'Alta Confianza' },
        ].map(opt => (
          <button
            key={opt.key}
            onClick={() => setFilterMode(opt.key)}
            className={filterMode === opt.key ? 'btn-primary' : 'btn-secondary'}
            style={{ fontSize: '0.75rem', padding: '0.3rem 0.7rem' }}
          >
            {opt.label}
          </button>
        ))}

        <span style={{ width: '1px', height: '18px', background: 'rgba(255,255,255,0.1)', margin: '0 0.2rem' }} />

        <ArrowUpDown size={15} color="var(--text-muted)" />
        {[
          { key: 'time', label: 'Hora' },
          { key: 'confidence', label: 'Confianza' },
        ].map(opt => (
          <button
            key={opt.key}
            onClick={() => setSortMode(opt.key)}
            className={sortMode === opt.key ? 'btn-primary' : 'btn-secondary'}
            style={{ fontSize: '0.75rem', padding: '0.3rem 0.7rem' }}
          >
            {opt.label}
          </button>
        ))}

        <span style={{ marginLeft: 'auto', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
          {visibleFixtures.length} de {fixtures.length} partidos
        </span>
      </div>

      {visibleFixtures.length === 0 ? (
        <div className="glass-panel" style={{ padding: '2rem', textAlign: 'center' }}>
          <p style={{ color: 'var(--text-muted)' }}>Ningún partido de hoy cumple este filtro. Probá con "Todos".</p>
        </div>
      ) : (
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(360px, 1fr))', gap: '1.2rem' }}>
        {visibleFixtures.map((fix) => {
          const hasPrediction = !!fix.prediction?.ensemble;
          const ens = fix.prediction?.ensemble || {};
          const models = fix.prediction?.models_breakdown || {};

          const isHomeWinner = ens.predicted_winner === 'HOME';
          const winProb = isHomeWinner ? ens.home_win_prob : ens.away_win_prob;
          const winnerTeam = isHomeWinner ? fix.home_team : fix.away_team;
          const odds = isHomeWinner ? fix.sb_home_odds : fix.sb_away_odds;

          const isValueBet = ens.value_ev_pct > 0;

          // Unidad correcta para el total (goles en fútbol: Liga MX y Leagues Cup)
          const totalUnitLabel = ['MX', 'LCUP'].includes(fix.league)
            ? 'goles'
            : (fix.league === 'MLB' || fix.league === 'KBO' ? 'carreras' : 'pts');
          const corners = ens.corners;


          return (
            <div key={fix.fixture_id} className="glass-panel glass-panel-interactive" style={{ padding: '1.2rem', position: 'relative' }}>
              {/* Top Bar: Date, Time & source tag */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.8rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                <span className="mono">
                  {fix.date}
                  {fix.time && fix.time !== 'TBD' ? ` • ${fix.time}` : ''}
                  {' • '}{fix.league}
                </span>
                {isValueBet ? (
                  <span className="badge badge-ev">
                    +EV {ens.value_ev_pct}% VALOR
                  </span>
                ) : (
                  <span style={{ fontSize: '0.75rem', opacity: 0.6 }}>Línea Normal</span>
                )}
              </div>
              {/* Badge de fuente de datos */}
              {fix.source && (
                <div style={{ marginBottom: '0.5rem' }}>
                  <span style={{
                    fontSize: '0.68rem',
                    padding: '2px 8px',
                    borderRadius: '10px',
                    background: fix.source !== 'Simulado' ? 'rgba(0,242,254,0.1)' : 'rgba(255,180,0,0.1)',
                    color: fix.source !== 'Simulado' ? '#00f2fe' : '#f5a623',
                    border: `1px solid ${fix.source !== 'Simulado' ? 'rgba(0,242,254,0.3)' : 'rgba(245,166,35,0.25)'}`,
                    fontWeight: fix.source !== 'Simulado' ? 700 : 400,
                    textShadow: fix.source !== 'Simulado' ? '0 0 10px rgba(0,242,254,0.45)' : 'none',
                  }}>
                    {fix.source !== 'Simulado' ? `🟢 Partido Real (${fix.source})` : '🟡 Simulado'}
                  </span>
                </div>
              )}

              {/* Match Teams & Odds */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr auto 1fr', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
                {/* Home Team */}
                <div style={{ textAlign: 'center' }}>
                  <TeamIcon teamName={fix.home_team} size={50} logoUrl={fix.home_logo} />
                  <div style={{ fontWeight: 700, fontSize: '0.95rem', color: ens.predicted_winner === 'HOME' ? '#00f2fe' : 'var(--text-main)' }}>
                    {fix.home_team}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Form: {(fix.home_form * 100).toFixed(0)}%</div>
                  <div className="mono" style={{ fontSize: '0.85rem', marginTop: '4px', fontWeight: 600, color: 'var(--accent-gold)' }}>
                    Cuota: {fix.sb_home_odds}
                  </div>
                </div>

                <div style={{ textAlign: 'center', fontSize: '0.8rem', fontWeight: 800, color: 'var(--text-dim)' }}>
                  VS
                </div>

                {/* Away Team */}
                <div style={{ textAlign: 'center' }}>
                  <TeamIcon teamName={fix.away_team} size={50} logoUrl={fix.away_logo} />
                  <div style={{ fontWeight: 700, fontSize: '0.95rem', color: ens.predicted_winner === 'AWAY' ? '#00f2fe' : 'var(--text-main)' }}>
                    {fix.away_team}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Form: {(fix.away_form * 100).toFixed(0)}%</div>
                  <div className="mono" style={{ fontSize: '0.85rem', marginTop: '4px', fontWeight: 600, color: 'var(--accent-gold)' }}>
                    Cuota: {fix.sb_away_odds}
                  </div>
                </div>
              </div>

              {/* Prediction Breakdown Bar */}
              <div style={{ background: 'rgba(0,0,0,0.3)', padding: '0.8rem', borderRadius: '10px', marginBottom: '0.8rem' }}>
                {!hasPrediction ? (
                  <div style={{ fontSize: '0.8rem', color: '#f5a623', display: 'flex', alignItems: 'flex-start', gap: '6px' }}>
                    <ShieldAlert size={16} style={{ flexShrink: 0, marginTop: '2px' }} />
                    <span>
                      El backend no pudo calcular la predicción de este partido.
                      {fix.prediction_error && (
                        <div className="mono" style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '4px', wordBreak: 'break-word' }}>
                          Error: {fix.prediction_error}
                        </div>
                      )}
                    </span>
                  </div>
                ) : (
                  <>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.82rem', marginBottom: '6px' }}>
                      <span>Ganador Probable (Ensemble):</span>
                      <strong style={{ color: '#00f2fe' }}>{winnerTeam} ({(winProb * 100).toFixed(1)}%)</strong>
                    </div>

                    {/* Progress bar */}
                    <div style={{ height: '6px', background: 'rgba(255,255,255,0.1)', borderRadius: '3px', overflow: 'hidden', marginBottom: '8px' }}>
                      <div style={{
                        width: `${ens.home_win_prob * 100}%`,
                        height: '100%',
                        background: 'linear-gradient(90deg, #2F8FFF 0%, #145FD1 100%)'
                      }} />
                    </div>

                    {/* Comparación rápida entre los 4 modelos base */}
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', fontSize: '0.75rem' }}>
                      <span className="badge badge-svm">SVM: {modelPct(models.SVM)} Local</span>
                      <span className="badge badge-nn">Red Neuronal: {modelPct(models.NeuralNetwork)} Local</span>
                      <span className="badge" style={{ background: 'rgba(251,146,60,0.12)', color: '#fb923c', border: '1px solid rgba(251,146,60,0.3)' }}>
                        XGBoost: {modelPct(models.XGBoost)} Local
                      </span>
                      <span className="badge" style={{ background: 'rgba(250,204,21,0.12)', color: '#facc15', border: '1px solid rgba(250,204,21,0.3)' }}>
                        LightGBM: {modelPct(models.LightGBM)} Local
                      </span>
                    </div>

                    {/* Modelo vs Mercado — solo cuando hay cuota REAL (the-odds-api.com)
                        de fondo; con cuota estimada no hay mercado real con qué comparar */}
                    {ens.blended_with_market && (
                      <div style={{ marginTop: '10px', paddingTop: '10px', borderTop: '1px solid rgba(255,255,255,0.06)' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '0.72rem', color: 'var(--text-muted)', marginBottom: '6px' }}>
                          <Scale size={13} />
                          Modelo vs Mercado (cuota real) — Local
                        </div>
                        <div style={{ display: 'flex', gap: '10px', fontSize: '0.78rem' }}>
                          <div style={{ flex: 1 }}>
                            <div style={{ color: 'var(--text-muted)', fontSize: '0.68rem' }}>Solo modelo</div>
                            <strong>{(ens.model_only_home_win_prob * 100).toFixed(1)}%</strong>
                          </div>
                          <div style={{ flex: 1 }}>
                            <div style={{ color: 'var(--text-muted)', fontSize: '0.68rem' }}>Mercado</div>
                            <strong>{(ens.market_implied_home_prob * 100).toFixed(1)}%</strong>
                          </div>
                          <div style={{ flex: 1 }}>
                            <div style={{ color: 'var(--text-muted)', fontSize: '0.68rem' }}>Final (mezcla)</div>
                            <strong style={{ color: '#00f2fe' }}>{(ens.home_win_prob * 100).toFixed(1)}%</strong>
                          </div>
                        </div>
                      </div>
                    )}
                  </>
                )}
              </div>

              {/* Markets Grid: Spread & Over/Under */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', fontSize: '0.8rem', marginBottom: '1rem' }}>
                <div style={{ background: 'rgba(255,255,255,0.03)', padding: '0.5rem', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.05)' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Línea Handicap:</span>
                  <div style={{ fontWeight: 700, color: 'var(--accent-blue)', marginTop: '2px' }}>
                    {ens.spread_pick ?? '—'}
                  </div>
                </div>
                <div style={{ background: 'rgba(255,255,255,0.03)', padding: '0.5rem', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.05)' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Over / Under Total:</span>
                  <div style={{ fontWeight: 700, color: 'var(--accent-emerald)', marginTop: '2px' }}>
                    {ens.over_under_pick ? `${ens.over_under_pick} (${ens.predicted_total} ${totalUnitLabel})` : '—'}
                  </div>
                </div>

                {/* Mercado de córners — ligas de fútbol (Liga MX, Leagues Cup) */}
                {['MX', 'LCUP'].includes(fix.league) && (
                  <div style={{ background: 'rgba(56, 189, 248,0.06)', padding: '0.5rem', borderRadius: '8px', border: '1px solid rgba(56, 189, 248,0.2)', gridColumn: '1 / -1' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Tiros de Esquina (Over/Under):</span>
                    <div style={{ fontWeight: 700, color: '#7DD3FC', marginTop: '2px' }}>
                      {corners
                        ? (corners.over_under_pick
                          ? `${corners.over_under_pick} (${corners.predicted_corners_total} córners)`
                          : `Proyección: ${corners.predicted_corners_total} córners`)
                        : 'Sin suficientes datos históricos de córners para esta liga todavía'}
                    </div>
                  </div>
                )}
              </div>

              {/* ¿Por qué esta predicción? — colapsable, usa fix.explanation
                  (generado en el backend a partir de los mismos features
                  que ya usa el modelo, ver _build_explanation en data_generator.py) */}
              {hasPrediction && fix.explanation && fix.explanation.length > 0 && (
                <div style={{ marginBottom: '0.8rem' }}>
                  <button
                    onClick={() => toggleExplanation(fix.fixture_id)}
                    style={{
                      display: 'flex', alignItems: 'center', gap: '6px', width: '100%',
                      background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.05)',
                      borderRadius: '8px', padding: '0.5rem 0.7rem', fontSize: '0.8rem',
                      color: 'var(--text-main)', cursor: 'pointer',
                    }}
                  >
                    <Lightbulb size={14} color="#f5a623" />
                    <span style={{ flex: 1, textAlign: 'left' }}>¿Por qué esta predicción?</span>
                    {expandedExplanations[fix.fixture_id] ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                  </button>
                  {expandedExplanations[fix.fixture_id] && (
                    <ul style={{
                      margin: '6px 0 0', padding: '0.6rem 0.9rem 0.6rem 1.6rem',
                      background: 'rgba(245,166,35,0.05)', border: '1px solid rgba(245,166,35,0.15)',
                      borderRadius: '8px', fontSize: '0.78rem', color: 'var(--text-muted)', lineHeight: 1.6,
                    }}>
                      {fix.explanation.map((reason, i) => <li key={i}>{reason}</li>)}
                    </ul>
                  )}
                </div>
              )}

              {/* Pick sugerido (solo informativo — sin acción de agregar a parlay) */}
              <div style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.05)',
                borderRadius: '10px', padding: '0.6rem 0.9rem', fontSize: '0.85rem'
              }}>
                <span style={{ color: 'var(--text-muted)' }}>Pick sugerido (Moneyline):</span>
                <strong style={{ color: hasPrediction ? '#00f2fe' : 'var(--text-muted)' }}>
                  {hasPrediction ? `${winnerTeam} (Cuota ${odds})` : 'Sin predicción disponible'}
                </strong>
              </div>
            </div>
          );
        })}
      </div>
      )}
    </div>
  );
}
