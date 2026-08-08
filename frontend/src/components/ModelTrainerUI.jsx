import React, { useState } from 'react';
import { Settings, RefreshCw, CheckCircle, Cpu } from 'lucide-react';
import { retrainModel } from '../services/api';

export default function ModelTrainerUI({ activeLeague, onRetrainSuccess }) {
  const [svmC, setSvmC] = useState(1.0);
  const [svmKernel, setSvmKernel] = useState('rbf');
  const [nnLearningRate, setNnLearningRate] = useState(0.001);
  const [nnHiddenSize, setNnHiddenSize] = useState(64);

  const [loading, setLoading] = useState(false);
  const [statusMessage, setStatusMessage] = useState(null);

  const handleRetrain = async () => {
    setLoading(true);
    setStatusMessage(null);
    try {
      const payload = {
        league: activeLeague,
        svm_c: Number(svmC),
        svm_kernel: svmKernel,
        nn_learning_rate: Number(nnLearningRate),
        nn_hidden_size: Number(nnHiddenSize)
      };
      const res = await retrainModel(payload);
      setStatusMessage(`¡Modelo para ${activeLeague} re-entrenado y guardado correctamente en backend!`);
      if (onRetrainSuccess) onRetrainSuccess();
    } catch (err) {
      console.error(err);
      setStatusMessage('Error al intentar reentrenar modelo.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: '700px', margin: '0 auto' }}>
      <div className="glass-panel" style={{ padding: '2rem' }}>
        <h2 style={{ fontSize: '1.4rem', fontWeight: 800, marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
          <Settings color="#A742FF" size={26} /> Re-Entrenamiento & Ajuste de Hiperparámetros ({activeLeague})
        </h2>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '1.5rem' }}>
          Configura y entrena nuevos pesos de aprendizaje para Support Vector Machines y Redes Neuronales sobre la liga {activeLeague}.
        </p>

        {statusMessage && (
          <div style={{ background: 'rgba(16, 185, 129, 0.15)', border: '1px solid #10b981', padding: '0.8rem 1rem', borderRadius: '12px', color: '#10b981', marginBottom: '1.2rem', display: 'flex', alignItems: 'center', gap: '0.6rem', fontSize: '0.9rem' }}>
            <CheckCircle size={20} />
            <span>{statusMessage}</span>
          </div>
        )}

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', marginBottom: '1.5rem' }}>
          {/* SVM Settings */}
          <div style={{ background: 'rgba(0,0,0,0.3)', padding: '1.2rem', borderRadius: '14px', borderTop: '3px solid #A742FF' }}>
            <h3 style={{ fontSize: '1rem', fontWeight: 700, color: '#A742FF', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <Cpu size={18} /> Support Vector Machine (SVM)
            </h3>

            <div style={{ marginBottom: '1rem' }}>
              <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>Parámetro de Regularización C</label>
              <input type="number" step="0.1" value={svmC} onChange={e => setSvmC(e.target.value)} style={{ width: '100%' }} />
            </div>

            <div>
              <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>Función Kernel</label>
              <select value={svmKernel} onChange={e => setSvmKernel(e.target.value)} style={{ width: '100%' }}>
                <option value="rbf">RBF (Radial Basis Function)</option>
                <option value="linear">Lineal</option>
                <option value="poly">Polinomial</option>
              </select>
            </div>
          </div>

          {/* Neural Network Settings */}
          <div style={{ background: 'rgba(0,0,0,0.3)', padding: '1.2rem', borderRadius: '14px', borderTop: '3px solid #7C1FFF' }}>
            <h3 style={{ fontSize: '1rem', fontWeight: 700, color: '#c084fc', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <Cpu size={18} /> Red Neuronal Multi-Capa (MLP)
            </h3>

            <div style={{ marginBottom: '1rem' }}>
              <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>Tasa de Aprendizaje (Learning Rate)</label>
              <input type="number" step="0.0005" value={nnLearningRate} onChange={e => setNnLearningRate(e.target.value)} style={{ width: '100%' }} />
            </div>

            <div>
              <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>Neuronas Capa Oculta Principal</label>
              <input type="number" step="16" value={nnHiddenSize} onChange={e => setNnHiddenSize(e.target.value)} style={{ width: '100%' }} />
            </div>
          </div>
        </div>

        <button onClick={handleRetrain} className="btn-primary" style={{ width: '100%', justifyContent: 'center', padding: '0.8rem' }} disabled={loading}>
          <RefreshCw size={18} className={loading ? 'pulse-glow' : ''} />
          {loading ? 'Entrenando Redes Neuronales & SVM en Servidor...' : `Re-Entrenar Modelos de ${activeLeague}`}
        </button>
      </div>
    </div>
  );
}
