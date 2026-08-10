import React, { useState, useRef } from 'react';
import { Cpu, Activity, BarChart2, Layers, TrendingUp, Settings } from 'lucide-react';

// Logos oficiales de liga, vía TheSportsDB (badge = fondo transparente).
// URLs estáticas confirmadas manualmente, no cambian -> se hardcodean acá
// en vez de pegarle a la API desde el frontend en cada render.
// LCUP: badge oficial de la Leagues Cup, confirmado contra
// thesportsdb.com/league/5281-leagues-cup
// NFL: badge oficial confirmado contra thesportsdb.com/league/4391-nfl
const LEAGUE_LOGOS = {
  LCUP: 'https://r2.thesportsdb.com/images/media/league/badge/8dqvox1650475851.png',
  MLB: 'https://r2.thesportsdb.com/images/media/league/badge/c5r83j1521893739.png',
  WNBA: 'https://r2.thesportsdb.com/images/media/league/badge/47llb31573154455.png',
  KBO: 'https://r2.thesportsdb.com/images/media/league/badge/qfr1hx1589707979.png',
  MX: 'https://r2.thesportsdb.com/images/media/league/badge/mav5rx1686157960.png',
  NFL: 'https://r2.thesportsdb.com/images/media/league/badge/g85fqz1662057187.png',
};

const LEAGUE_LABELS = {
  LCUP: 'Leagues Cup 2026',
  MLB: 'MLB',
  WNBA: 'WNBA',
  KBO: 'KBO (Corea)',
  MX: 'Liga MX',
  NFL: 'NFL (Pretemporada)',
};

export default function Header({ activeLeague, setActiveLeague, activeTab, setActiveTab, leagues }) {
  const logoRef = useRef(null);
  const [tilt, setTilt] = useState({ x: 0, y: 0 });

  const handleLogoMove = (e) => {
    const el = logoRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const px = (e.clientX - rect.left) / rect.width - 0.5;
    const py = (e.clientY - rect.top) / rect.height - 0.5;
    setTilt({ x: py * -22, y: px * 26 });
  };
  const handleLogoLeave = () => setTilt({ x: 0, y: 0 });

  const tabs = [
    { id: 'fixtures', label: 'Partidos 2026 (+EV)', icon: Activity },
    { id: 'predictor', label: 'Simulador 1v1', icon: Cpu },
    { id: 'parlay', label: 'Creador de Parlays', icon: Layers },
    { id: 'battle', label: 'Batalla de Modelos', icon: BarChart2 },
    { id: 'backtest', label: 'Simulador de ROI', icon: TrendingUp },
    { id: 'train', label: 'Re-Entrenamiento ML', icon: Settings },
  ];

  return (
    <header className="glass-panel" style={{ padding: '1.2rem 2rem', marginBottom: '1.5rem', borderRadius: '20px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
        {/* Logo & Title — núcleo 3D con los modelos ML orbitando el meta-ensemble */}
        <div
          ref={logoRef}
          onMouseMove={handleLogoMove}
          onMouseLeave={handleLogoLeave}
          className="logo3d-scene"
          style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}
        >
          <div
            className="logo3d-tilt"
            style={{ transform: `rotateX(${tilt.x}deg) rotateY(${tilt.y}deg)` }}
          >
            <div className="logo3d-core">
              <div className="orbit-tilt orbit-1">
                <div className="orbit-spin">
                  <span className="electron e1" />
                </div>
              </div>
              <div className="orbit-tilt orbit-2">
                <div className="orbit-spin reverse">
                  <span className="electron e2" />
                </div>
              </div>
              <div className="orbit-tilt orbit-3">
                <div className="orbit-spin slow">
                  <span className="electron e3" />
                </div>
              </div>
              <div className="logo3d-face">
                <Cpu size={24} color="#ffffff" />
              </div>
              <div className="logo3d-shine" />
            </div>
          </div>

          <div
            className="logo3d-tilt"
            style={{ transform: `rotateX(${tilt.x * 0.35}deg) rotateY(${tilt.y * 0.35}deg) translateZ(4px)` }}
          >
            <h1 className="logo3d-text" style={{ fontSize: '1.5rem', fontWeight: 800, letterSpacing: '-0.5px' }}>
              PARLEYS <span className="logo3d-shimmer">ALOR</span> <span style={{ fontSize: '0.75rem', verticalAlign: 'super', background: 'rgba(47, 143, 255, 0.2)', padding: '2px 8px', borderRadius: '10px', color: '#2F8FFF' }}>2026 v1.0</span>
            </h1>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
              Motor Inteligente: XGBoost + LightGBM + SVM + Redes Neuronales + Meta-Ensemble + Random Forest
            </p>
          </div>
        </div>

        {/* League Selector Pills */}
        <div style={{ display: 'flex', gap: '0.5rem', background: 'rgba(0,0,0,0.3)', padding: '5px', borderRadius: '14px', flexWrap: 'wrap' }}>
          {['LCUP', 'MLB', 'WNBA', 'KBO', 'MX', 'NFL'].map(lg => (
            <button
              key={lg}
              onClick={() => setActiveLeague(lg)}
              className={activeLeague === lg ? 'btn-secondary btn-active-league' : 'btn-secondary'}
              style={{ padding: '0.45rem 0.9rem', borderRadius: '10px', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}
            >
              <img
                src={LEAGUE_LOGOS[lg]}
                alt={lg}
                style={{ width: '20px', height: '20px', objectFit: 'contain', flexShrink: 0 }}
                onError={(e) => { e.target.style.display = 'none'; }}
              />
              {LEAGUE_LABELS[lg]}
            </button>
          ))}
        </div>
      </div>

      {/* Tabs Row */}
      <nav style={{ display: 'flex', gap: '0.5rem', marginTop: '1.2rem', borderTop: '1px solid rgba(255,255,255,0.06)', paddingTop: '1rem', overflowX: 'auto' }}>
        {tabs.map(tab => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                background: isActive ? 'linear-gradient(135deg, rgba(47, 143, 255, 0.15) 0%, rgba(20, 95, 209, 0.15) 100%)' : 'transparent',
                border: isActive ? '1px solid rgba(47, 143, 255, 0.4)' : '1px solid transparent',
                color: isActive ? '#2F8FFF' : 'var(--text-muted)',
                padding: '0.6rem 1.1rem',
                borderRadius: '12px',
                cursor: 'pointer',
                fontWeight: isActive ? 700 : 500,
                fontSize: '0.9rem',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                whiteSpace: 'nowrap',
                transition: 'all 0.2s ease'
              }}
            >
              <Icon size={18} />
              {tab.label}
            </button>
          );
        })}
      </nav>
    </header>
  );
}
