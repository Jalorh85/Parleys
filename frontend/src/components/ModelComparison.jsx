import React, { useState, useEffect, useMemo } from 'react';
import { BarChart2, Award, Zap, Cpu, Radar as RadarIcon } from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell, LabelList,
  RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, Legend
} from 'recharts';
import { fetchMetrics } from '../services/api';

// Mismo criterio de color que ya usaban las cards manuales -- se extrae acá
// para reutilizarlo también en las gráficas de Recharts, así todo el
// componente (cards, barras, radar) habla el mismo lenguaje visual.
function colorForModel(model) {
  const isEnsemble = model.includes('Ensemble');
  const isSVM = model.includes('SVM');
  const isXGB = model.includes('XGBoost');
  const isLGBM = model.includes('LightGBM');
  return isEnsemble ? '#2F8FFF' : (isSVM ? '#00D8FF' : (isXGB ? '#fb923c' : (isLGBM ? '#facc15' : '#7DD3FC')));
}

function shortName(model) {
  if (model.includes('SVM')) return 'SVM';
  if (model.includes('MLP') || model.includes('Redes Neuronales')) return 'MLP';
  if (model.includes('XGBoost')) return 'XGBoost';
  if (model.includes('LightGBM')) return 'LightGBM';
  if (model.includes('Ensemble')) return 'Ensemble';
  return model;
}

// Normaliza un valor a 0-100 relativo al propio set de modelos, para que el
// radar compare "quién va mejor relativo a los demás" sin depender de una
// escala absoluta arbitraria. higherIsBetter=false invierte la escala
// (para MAE, donde menos error es mejor).
function normalize(values, value, higherIsBetter = true) {
  const min = Math.min(...values);
  const max = Math.max(...values);
  if (max === min) return 100;
  const pct = (value - min) / (max - min);
  return Math.round((higherIsBetter ? pct : 1 - pct) * 1000) / 10;
}

function ChartTooltip({ active, payload, unit }) {
  if (!active || !payload || !payload.length) return null;
  const p = payload[0].payload;
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
      <div style={{ fontWeight: 700, marginBottom: '4px', color: p.color }}>{p.model}</div>
      <div style={{ color: 'var(--text-muted)' }}>{p.value}{unit}</div>
    </div>
  );
}

function RadarTooltip({ active, payload, label }) {
  if (!active || !payload || !payload.length) return null;
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
      <div style={{ fontWeight: 700, marginBottom: '4px' }}>{label}</div>
      {payload.map(p => (
        <div key={p.dataKey} style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem' }}>
          <span style={{ color: p.color, fontWeight: 600 }}>{p.dataKey}</span>
          <span style={{ color: 'var(--text-muted)' }}>{p.value}</span>
        </div>
      ))}
    </div>
  );
}

export default function ModelComparison({ activeLeague }) {
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetchMetrics(activeLeague)
      .then(res => setMetrics(res))
      .catch(err => console.error(err))
      .finally(() => setLoading(false));
  }, [activeLeague]);

  if (loading) {
    return (
      <div className="glass-panel" style={{ padding: '3rem', textAlign: 'center' }}>
        <Zap className="pulse-glow" size={48} color="#145FD1" style={{ margin: '0 auto 1rem' }} />
        <h3>Calculando métricas de precisión...</h3>
      </div>
    );
  }

  const comparison = metrics?.comparison || [];

  const chartModels = useMemo(
    () => comparison.map(item => ({
      ...item,
      short: shortName(item.model),
      color: colorForModel(item.model),
      isEnsemble: item.model.includes('Ensemble'),
    })),
    [comparison]
  );

  const accuracyRanked = useMemo(
    () => [...chartModels].sort((a, b) => b.win_accuracy - a.win_accuracy),
    [chartModels]
  );
  const maeRanked = useMemo(
    () => [...chartModels].sort((a, b) => a.total_mae - b.total_mae),
    [chartModels]
  );

  // Radar: 3 ejes normalizados relativo al propio set de modelos -- el
  // Ensemble se dibuja relleno y encima, el resto como contorno fino, para
  // que se vea de un vistazo cómo el área del Ensemble cubre a las demás.
  const radarData = useMemo(() => {
    if (!chartModels.length) return [];
    const accs = chartModels.map(m => m.win_accuracy);
    const maes = chartModels.map(m => m.total_mae);
    const rois = chartModels.map(m => m.roi_est);
    const axes = [
      { axis: 'Precisión', key: 'win_accuracy', values: accs, higherIsBetter: true },
      { axis: 'Error bajo (MAE⁻¹)', key: 'total_mae', values: maes, higherIsBetter: false },
      { axis: 'ROI estimado', key: 'roi_est', values: rois, higherIsBetter: true },
    ];
    return axes.map(({ axis, key, values, higherIsBetter }) => {
      const point = { axis };
      chartModels.forEach(m => { point[m.short] = normalize(values, m[key], higherIsBetter); });
      return point;
    });
  }, [chartModels]);

  return (
    <div style={{ display: 'grid', gap: '1.5rem' }}>
      {/* Overview Cards */}
      <div className="glass-panel" style={{ padding: '1.5rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.2rem' }}>
          <div>
            <h2 style={{ fontSize: '1.3rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <BarChart2 color="#145FD1" size={24} /> Batalla de Modelos ML - {activeLeague}
            </h2>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
              Comparativa empírica entre Support Vector Machines (SVM), Redes Neuronales MLP y Meta-Ensemble
            </p>
          </div>
          <span className="badge badge-nn">Muestra de Evaluación: {metrics?.sample_size} Partidos</span>
        </div>

        {/* Visual Bar Comparison */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.2rem', marginBottom: '1.5rem' }}>
          {comparison.map((item, idx) => {
            const isEnsemble = item.model.includes('Ensemble');
            const isSVM = item.model.includes('SVM');
            const isXGB = item.model.includes('XGBoost');
            const isLGBM = item.model.includes('LightGBM');
            const color = isEnsemble ? '#2F8FFF' : (isSVM ? '#00D8FF' : (isXGB ? '#fb923c' : (isLGBM ? '#facc15' : '#7DD3FC')));

            return (
              <div key={idx} style={{ background: 'rgba(0,0,0,0.3)', border: `1px solid ${color}40`, borderRadius: '16px', padding: '1.2rem' }}>
                <div style={{ fontSize: '0.9rem', fontWeight: 700, color: color, marginBottom: '0.8rem' }}>
                  {item.model}
                </div>

                {/* Accuracy Gauge */}
                <div style={{ marginBottom: '1rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: '4px' }}>
                    <span>Precisión (Win Accuracy):</span>
                    <strong style={{ fontSize: '1.1rem', color: '#ffffff' }}>{item.win_accuracy}%</strong>
                  </div>
                  <div style={{ height: '10px', background: 'rgba(255,255,255,0.1)', borderRadius: '5px', overflow: 'hidden' }}>
                    <div style={{ width: `${item.win_accuracy}%`, height: '100%', background: color }} />
                  </div>
                </div>

                {/* MAE & ROI */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', fontSize: '0.8rem' }}>
                  <div style={{ background: 'rgba(255,255,255,0.04)', padding: '0.5rem', borderRadius: '8px' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Error Totales (MAE):</span>
                    <div style={{ fontWeight: 700, marginTop: '2px' }}>{item.total_mae} pts</div>
                  </div>
                  <div style={{ background: 'rgba(255,255,255,0.04)', padding: '0.5rem', borderRadius: '8px' }}>
                    <span style={{ color: 'var(--text-muted)' }}>ROI Estimado:</span>
                    <div style={{ fontWeight: 700, color: item.roi_est > 0 ? '#10b981' : '#ef4444', marginTop: '2px' }}>
                      {item.roi_est > 0 ? `+${item.roi_est}%` : `${item.roi_est}%`}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Leaderboard de precisión (bar chart) */}
        {accuracyRanked.length > 0 && (
          <div style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '16px', padding: '1.2rem', marginBottom: '1.2rem' }}>
            <div style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-main)', marginBottom: '0.8rem' }}>
              Precisión de ganador por modelo
            </div>
            <div style={{ width: '100%', height: 240 }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={accuracyRanked} margin={{ top: 24, right: 16, left: -12, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" vertical={false} />
                  <XAxis dataKey="short" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={{ stroke: 'rgba(255,255,255,0.1)' }} tickLine={false} />
                  <YAxis
                    tickFormatter={v => `${v}%`}
                    domain={[0, dataMax => Math.min(100, Math.ceil((dataMax + 8) / 5) * 5)]}
                    tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
                    axisLine={false}
                    tickLine={false}
                    width={40}
                  />
                  <Tooltip content={<ChartTooltip unit="%" />} cursor={{ fill: 'rgba(255,255,255,0.04)' }} />
                  <Bar dataKey="win_accuracy" radius={[8, 8, 0, 0]} maxBarSize={64}>
                    {accuracyRanked.map(m => (
                      <Cell key={m.model} fill={m.color} fillOpacity={m.isEnsemble ? 1 : 0.55} stroke={m.isEnsemble ? m.color : 'transparent'} strokeWidth={2} />
                    ))}
                    <LabelList dataKey="win_accuracy" position="top" formatter={v => `${v}%`} style={{ fill: '#ffffff', fontSize: 12, fontWeight: 700 }} />
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {/* MAE + Radar lado a lado */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1.2rem', marginBottom: '1.5rem' }}>
          <div style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '16px', padding: '1.2rem' }}>
            <div style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-main)', marginBottom: '2px' }}>
              Error de predicción (MAE total)
            </div>
            <p style={{ margin: '0 0 0.8rem', fontSize: '0.72rem', color: 'var(--text-muted)' }}>
              Puntos/goles de diferencia vs. resultado real — menos es mejor
            </p>
            <div style={{ width: '100%', height: 220 }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={maeRanked} layout="vertical" margin={{ top: 4, right: 24, left: 8, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" horizontal={false} />
                  <XAxis type="number" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} />
                  <YAxis type="category" dataKey="short" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} width={78} />
                  <Tooltip content={<ChartTooltip unit=" pts" />} cursor={{ fill: 'rgba(255,255,255,0.04)' }} />
                  <Bar dataKey="total_mae" radius={[0, 8, 8, 0]} maxBarSize={22}>
                    {maeRanked.map(m => (
                      <Cell key={m.model} fill={m.color} fillOpacity={m.isEnsemble ? 1 : 0.55} stroke={m.isEnsemble ? m.color : 'transparent'} strokeWidth={2} />
                    ))}
                    <LabelList dataKey="total_mae" position="right" style={{ fill: '#ffffff', fontSize: 11, fontWeight: 700 }} />
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '16px', padding: '1.2rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '2px' }}>
              <RadarIcon size={14} color="#2F8FFF" />
              <div style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-main)' }}>
                Ensemble vs. modelos individuales
              </div>
            </div>
            <p style={{ margin: '0 0 0.4rem', fontSize: '0.72rem', color: 'var(--text-muted)' }}>
              Ejes normalizados 0-100 relativo a este set — más área es mejor
            </p>
            <div style={{ width: '100%', height: 220 }}>
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart data={radarData} outerRadius="70%">
                  <PolarGrid stroke="rgba(255,255,255,0.08)" />
                  <PolarAngleAxis dataKey="axis" tick={{ fill: 'var(--text-muted)', fontSize: 10 }} />
                  <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fill: 'var(--text-muted)', fontSize: 9 }} axisLine={false} tickCount={3} />
                  <Tooltip content={<RadarTooltip />} />
                  {chartModels.map(m => (
                    <Radar
                      key={m.short}
                      name={m.short}
                      dataKey={m.short}
                      stroke={m.color}
                      fill={m.color}
                      fillOpacity={m.isEnsemble ? 0.35 : 0.04}
                      strokeWidth={m.isEnsemble ? 2.5 : 1.25}
                    />
                  ))}
                  <Legend wrapperStyle={{ fontSize: '0.68rem' }} formatter={(value) => <span style={{ color: 'var(--text-muted)' }}>{value}</span>} />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* Detailed Metrics Table */}
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem', textAlign: 'left' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.1)', color: 'var(--text-muted)' }}>
                <th style={{ padding: '0.8rem' }}>Modelo / Algoritmo</th>
                <th style={{ padding: '0.8rem' }}>Arquitectura / Kernel</th>
                <th style={{ padding: '0.8rem' }}>Win Rate %</th>
                <th style={{ padding: '0.8rem' }}>Over/Under MAE</th>
                <th style={{ padding: '0.8rem' }}>Rentabilidad Estimada</th>
              </tr>
            </thead>
            <tbody>
              {comparison.map((item, idx) => (
                <tr key={idx} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                  <td style={{ padding: '0.8rem', fontWeight: 700 }}>{item.model}</td>
                  <td style={{ padding: '0.8rem', color: 'var(--text-muted)' }}>
                    {item.model.includes('SVM')
                      ? 'Kernel RBF (C=1.0, Platt Scaling)'
                      : item.model.includes('MLP')
                        ? 'MLP (64, 32 ReLU, Adam)'
                        : item.model.includes('XGBoost')
                          ? 'Gradient Boosting (150 árboles, depth=4)'
                          : item.model.includes('LightGBM')
                            ? 'Gradient Boosting (150 árboles, leaf-wise)'
                            : item.model.includes('Ensemble')
                              ? 'Weighted Meta-Voting'
                              : 'Random Forest (100 árboles, depth=8)'}
                  </td>
                  <td style={{ padding: '0.8rem', fontWeight: 700, color: '#2F8FFF' }}>{item.win_accuracy}%</td>
                  <td style={{ padding: '0.8rem' }}>{item.total_mae} pts</td>
                  <td style={{ padding: '0.8rem', fontWeight: 700, color: item.roi_est > 0 ? '#10b981' : '#ef4444' }}>
                    {item.roi_est > 0 ? `+${item.roi_est}%` : `${item.roi_est}%`}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
