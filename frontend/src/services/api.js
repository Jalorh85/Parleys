// En desarrollo usa localhost. En producción usa VITE_API_BASE del archivo .env
const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000/api';

export async function fetchLeagues() {
  const res = await fetch(`${API_BASE}/leagues`);
  if (!res.ok) throw new Error('Error al cargar ligas');
  return res.json();
}

export async function fetchFixtures(league, date = null) {
  const params = new URLSearchParams({ league });
  if (date) params.append('date', date);
  const res = await fetch(`${API_BASE}/fixtures?${params}`);
  if (!res.ok) throw new Error(`Error al cargar partidos de ${league}`);
  return res.json();
}

export async function predictMatchup(payload) {
  const res = await fetch(`${API_BASE}/predict`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!res.ok) throw new Error('Error al realizar predicción');
  return res.json();
}

export async function fetchMetrics(league) {
  const res = await fetch(`${API_BASE}/metrics?league=${league}`);
  if (!res.ok) throw new Error('Error al cargar métricas de modelos');
  return res.json();
}

export async function runBacktest(payload) {
  const res = await fetch(`${API_BASE}/backtest`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!res.ok) throw new Error('Error al ejecutar backtest');
  return res.json();
}

export async function calculateParlay(legs, stake) {
  const res = await fetch(`${API_BASE}/parlay`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ legs, stake })
  });
  if (!res.ok) throw new Error('Error al calcular combinada');
  return res.json();
}

export async function retrainModel(payload) {
  const res = await fetch(`${API_BASE}/retrain`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!res.ok) throw new Error('Error al reentrenar modelo');
  return res.json();
}
