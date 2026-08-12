import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import DailyFixtures from './components/DailyFixtures';
import AccuracyWidget from './components/AccuracyWidget';
import BankrollChart from './components/BankrollChart';
import MatchPredictor from './components/MatchPredictor';
import ParlayBuilder from './components/ParlayBuilder';
import ModelComparison from './components/ModelComparison';
import BacktestSimulator from './components/BacktestSimulator';
import ModelTrainerUI from './components/ModelTrainerUI';
import { fetchLeagues, fetchFixtures } from './services/api';

// Helpers de fecha
function toDateStr(d) {
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}
function getToday() { return toDateStr(new Date()); }
function getTomorrow() { const d = new Date(); d.setDate(d.getDate() + 1); return toDateStr(d); }
function getDayAfter() { const d = new Date(); d.setDate(d.getDate() + 2); return toDateStr(d); }
function formatLabel(dateStr) {
  const today = getToday();
  const tomorrow = getTomorrow();
  if (dateStr === today) return 'Hoy';
  if (dateStr === tomorrow) return 'Mañana';
  const [y, m, d] = dateStr.split('-');
  return `${d}/${m}/${y}`;
}

export default function App() {
  const [activeLeague, setActiveLeague] = useState('LCUP');
  const [activeTab, setActiveTab] = useState('fixtures');
  const [selectedDate, setSelectedDate] = useState(getToday()); // hoy por defecto

  const [leagues, setLeagues] = useState({});
  const [fixtures, setFixtures] = useState([]);
  const [loadingFixtures, setLoadingFixtures] = useState(false);
  const [fixtureSource, setFixtureSource] = useState(null); // 'ESPN' | 'TheSportsDB' | 'Simulado'
  const [fetchError, setFetchError] = useState(null); // mensaje de error al cargar
  const [noDataMessage, setNoDataMessage] = useState(null); // mensaje de "sin partidos reales" del backend

  const [parlayLegs, setParlayLegs] = useState([]);

  // Cargar ligas
  useEffect(() => {
    fetchLeagues()
      .then(data => setLeagues(data))
      .catch(err => console.error(err));
  }, []);

  // Cargar partidos cuando cambia liga o fecha
  const loadLeagueFixtures = (league = activeLeague, date = selectedDate) => {
    setLoadingFixtures(true);
    setFixtureSource(null);
    setFetchError(null);
    setNoDataMessage(null);
    fetchFixtures(league, date)
      .then(data => {
        if (data.error) {
          throw new Error(data.error);
        }
        const list = data.fixtures || [];
        setFixtures(list);
        // Detectar si los datos son reales o simulados
        if (list.length > 0) {
          setFixtureSource(list[0].source || null);
        } else {
          // Backend ya no rellena con partidos simulados cuando no hay
          // reales -- trae un mensaje explicando la ausencia (ver main.py).
          setNoDataMessage(data.message || null);
        }
      })
      .catch(err => {
        console.error(err);
        setFetchError(err.message || 'No se pudo conectar con el servidor. ¿Está corriendo el backend?');
        setFixtures([]);
      })
      .finally(() => setLoadingFixtures(false));
  };

  useEffect(() => {
    loadLeagueFixtures(activeLeague, selectedDate);
  }, [activeLeague, selectedDate]);

  // Parlay handlers
  const handleAddToParlay = (leg) => {
    if (!parlayLegs.some(l => l.fixture_id === leg.fixture_id)) {
      setParlayLegs([...parlayLegs, leg]);
    }
  };
  const handleRemoveParlayLeg = (fixture_id) => {
    setParlayLegs(parlayLegs.filter(l => l.fixture_id !== fixture_id));
  };
  const handleClearParlay = () => setParlayLegs([]);

  // Botones de fecha rápida
  const quickDates = [getToday(), getTomorrow(), getDayAfter()];

  return (
    <div style={{ maxWidth: '1400px', margin: '0 auto', padding: '1.5rem 1rem 3rem' }}>
      <Header
        activeLeague={activeLeague}
        setActiveLeague={setActiveLeague}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        leagues={leagues}
      />

      {/* ── Precisión Real (solo en pestaña de partidos) ── */}
      {activeTab === 'fixtures' && <AccuracyWidget activeLeague={activeLeague} />}
      {activeTab === 'fixtures' && <BankrollChart defaultLeague={activeLeague} />}

      {/* ── Selector de Fecha (solo en pestaña de partidos) ── */}
      {activeTab === 'fixtures' && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: '0.75rem',
          margin: '1rem 0', flexWrap: 'wrap'
        }}>
          {/* Botones rápidos: Hoy / Mañana / Pasado */}
          {quickDates.map(d => (
            <button
              key={d}
              onClick={() => setSelectedDate(d)}
              className={selectedDate === d ? 'btn-primary' : 'btn-secondary'}
              style={{ fontSize: '0.82rem', padding: '0.4rem 1rem' }}
            >
              {formatLabel(d)}
            </button>
          ))}

          {/* Selector de fecha libre */}
          <input
            type="date"
            value={selectedDate}
            onChange={e => setSelectedDate(e.target.value)}
            style={{
              background: 'rgba(255,255,255,0.07)',
              border: '1px solid rgba(255,255,255,0.15)',
              borderRadius: '8px',
              color: 'var(--text-main)',
              padding: '0.4rem 0.75rem',
              fontSize: '0.82rem',
              cursor: 'pointer',
            }}
          />

          {/* Badge de fuente de datos */}
          {fixtureSource && (
            <span style={{
              marginLeft: 'auto',
              fontSize: '0.75rem',
              padding: '0.3rem 0.75rem',
              borderRadius: '20px',
              background: fixtureSource !== 'Simulado'
                ? 'rgba(0,242,254,0.12)' : 'rgba(255,180,0,0.12)',
              color: fixtureSource !== 'Simulado' ? '#00f2fe' : '#f5a623',
              border: `1px solid ${fixtureSource !== 'Simulado' ? 'rgba(0,242,254,0.35)' : 'rgba(245,166,35,0.3)'}`,
              textShadow: fixtureSource !== 'Simulado' ? '0 0 12px rgba(0,242,254,0.5)' : 'none',
            }}>
              {fixtureSource !== 'Simulado' ? `🟢 Partidos Reales (${fixtureSource})` : '🟡 Datos Simulados'}
            </span>
          )}
        </div>
      )}

      <main style={{ marginTop: '0.5rem' }}>
        {activeTab === 'fixtures' && (
          <DailyFixtures
            fixtures={fixtures}
            loading={loadingFixtures}
            error={fetchError}
            onRetry={() => loadLeagueFixtures()}
            selectedDate={selectedDate}
            noDataMessage={noDataMessage}
          />
        )}

        {activeTab === 'predictor' && (
          <MatchPredictor
            activeLeague={activeLeague}
            leagues={leagues}
          />
        )}

        {activeTab === 'parlay' && (
          <ParlayBuilder
            parlayLegs={parlayLegs}
            onRemoveLeg={handleRemoveParlayLeg}
            onClearParlay={handleClearParlay}
          />
        )}

        {activeTab === 'battle' && (
          <ModelComparison
            activeLeague={activeLeague}
          />
        )}

        {activeTab === 'backtest' && (
          <BacktestSimulator
            activeLeague={activeLeague}
          />
        )}

        {activeTab === 'train' && (
          <ModelTrainerUI
            activeLeague={activeLeague}
            onRetrainSuccess={() => loadLeagueFixtures()}
          />
        )}
      </main>

      <footer style={{ textAlign: 'center', marginTop: '4rem', color: 'var(--text-muted)', fontSize: '0.85rem', borderTop: '1px solid rgba(255,255,255,0.06)', paddingTop: '1.5rem' }}>
        <p>PARLEYS ALOR 2026 • Predicciones Deportivas Basadas en Datos con XGBoost + LightGBM + SVM + Redes Neuronales + Meta-Ensemble + Random Forest</p>
        <p>Dasarrollado por MSC. Juan Antonio Alor Hernández © 2026  Todos los derechos reservados</p>

      </footer>
    </div>
  );
}
