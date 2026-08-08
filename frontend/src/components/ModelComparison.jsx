import React, { useState, useEffect } from 'react';
import { BarChart2, Award, Zap, Cpu } from 'lucide-react';
import { fetchMetrics } from '../services/api';

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
