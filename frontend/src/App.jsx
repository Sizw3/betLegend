import { useState } from 'react'
import './index.css'
import MatchExplorer from './components/MatchExplorer'
import BetSlip from './components/BetSlip'
import { API_BASE_URL } from './config'

const MODE_META = {
  low_risk: { label: '🛡️ Low Risk', short: 'Low Risk', desc: 'Only near-certain outcomes. Extreme safety nets.', btnClass: 'btn-low', badgeClass: 'badge-low', fillClass: 'fill-low', activeBtnClass: 'active-low' },
  conservative: { label: '⚖️ Conservative', short: 'Conservative', desc: 'Balanced. High-confidence markets.', btnClass: 'btn-cons', badgeClass: 'badge-cons', fillClass: 'fill-cons', activeBtnClass: 'active-cons' },
  high_risk: { label: '🔥 High Risk', short: 'High Risk', desc: 'Higher odds. Straight wins, BTTS. For the bold.', btnClass: 'btn-high', badgeClass: 'badge-high', fillClass: 'fill-high', activeBtnClass: 'active-high' },
}

function MlBar({ label, value }) {
  const pct = Math.round(value * 100)
  const color = pct >= 65 ? 'var(--green)' : pct >= 50 ? 'var(--blue)' : 'var(--muted)'
  return (
    <div style={{ marginBottom: '.5rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '.75rem', marginBottom: '.2rem' }}>
        <span style={{ color: 'var(--muted)' }}>{label}</span>
        <span style={{ fontWeight: 700, color }}>{pct}%</span>
      </div>
      <div className="conf-bar-bg" style={{ marginBottom: 0 }}>
        <div style={{ height: '100%', width: `${pct}%`, background: color, borderRadius: 99, transition: 'width .6s ease' }} />
      </div>
    </div>
  )
}

function PredictionDetail({ prediction, onReset, onAddToSlip }) {
  const meta = MODE_META.conservative // Default for detail view
  return (
    <div className="card slide-up" style={{ marginBottom: 0 }}>
      <div className="pred-matchup">{prediction.stats_summary.home?.name}<span className="pred-vs">vs</span>{prediction.stats_summary.away?.name}</div>
      <div className="pred-pick">{prediction.recommendation}</div>
      <div className="pred-betway">Betway → {prediction.betway_market}</div>

      <div className="confidence-row" style={{ marginTop: '1.5rem' }}><span className="conf-label">Confidence</span><span className="conf-value">{prediction.confidence}%</span></div>
      <div className="conf-bar-bg"><div className={`conf-bar-fill ${meta.fillClass}`} style={{ width: `${prediction.confidence}%` }} /></div>

      {prediction.ml_probabilities && (
        <div style={{ marginBottom: '1.5rem' }}>
          {Object.entries(prediction.ml_probabilities).map(([k, v]) => (
            <MlBar key={k} label={k.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())} value={v} />
          ))}
        </div>
      )}

      <div className="ranked-title">System Rationale</div>
      <p style={{ fontSize: '.85rem', color: 'var(--muted)', marginBottom: '1.5rem' }}>{prediction.rationale}</p>

      <button className="reset-btn" onClick={onReset}>← Back to Explorer</button>
    </div>
  )
}

export default function App() {
  const [slip, setSlip] = useState([])
  const [analyzing, setAnalyzing] = useState(false)
  const [activePrediction, setActivePrediction] = useState(null)
  const [mode, setMode] = useState('conservative')
  const [mobileSlipOpen, setMobileSlipOpen] = useState(false)

  const addToSlip = (match) => {
    if (slip.find(s => s.home === match.home && s.away === match.away)) return
    setSlip([...slip, { ...match, prediction: null, mode }])
  }

  const buildSlip = async () => {
    setAnalyzing(true)
    try {
      const matchesToAnalyze = slip.filter(s => !s.prediction)
      const res = await fetch(`${API_BASE_URL}/api/multi-analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          matches: matchesToAnalyze.map(m => ({
            home_team: m.home,
            away_team: m.away,
            mode: m.mode
          }))
        })
      })

      if (res.ok) {
        const results = await res.json()
        const newSlip = [...slip]
        let resIndex = 0
        for (let i = 0; i < newSlip.length; i++) {
          if (!newSlip[i].prediction) {
            newSlip[i].prediction = results[resIndex++]
          }
        }
        setSlip(newSlip)
      }
    } catch (e) {
      console.error("Multi-analysis failed", e)
    } finally {
      setAnalyzing(false)
    }
  }

  const removeFromSlip = (index) => {
    setSlip(slip.filter((_, i) => i !== index))
  }

  return (
    <div id="root">
      <header className="header">
        <div className="header-logo">Bet Legend <span style={{ color: 'var(--green)', fontSize: '1rem', verticalAlign: 'middle' }}>V4.2</span></div>
        <div className="header-sub">Multi-Analysis Engine · SportDB Discovery</div>
      </header>

      <div className="premium-dashboard slide-up">
        {activePrediction ? (
          <PredictionDetail
            prediction={activePrediction}
            onReset={() => setActivePrediction(null)}
          />
        ) : (
          <MatchExplorer onAddToSlip={addToSlip} />
        )}

        <div className="main-panel">
          <div className="card">
            <div className="ranked-title" style={{ marginBottom: '1rem' }}>Global Analysis Mode</div>
            <div className="mode-toggle">
              {Object.entries(MODE_META).map(([key, m]) => (
                <button key={key} className={`mode-btn ${mode === key ? m.activeBtnClass : ''}`} onClick={() => setMode(key)}>{m.label}</button>
              ))}
            </div>
            <p className="mode-desc">{MODE_META[mode].desc}</p>
          </div>

          <div className="card" style={{ background: 'rgba(0,180,255,0.02)', borderColor: 'rgba(0,180,255,0.1)' }}>
            <div className="ranked-title">Workflow Instructions</div>
            <ul style={{ fontSize: '.8rem', color: 'var(--muted)', paddingLeft: '1.2rem', marginTop: '.5rem' }}>
              <li>1. Search & Filter for matches in the Explorer.</li>
              <li>2. Click "Add to Slip" for games you want to analyze.</li>
              <li>3. Click "Run Multi-Analysis" in the slip to generate the report.</li>
            </ul>
          </div>
        </div>

        <BetSlip
          slip={slip}
          onRemove={removeFromSlip}
          onClear={() => setSlip([])}
          onBuildSlip={buildSlip}
          analyzing={analyzing}
          mobileOpen={mobileSlipOpen}
          onClose={() => setMobileSlipOpen(false)}
        />

        {mobileSlipOpen && <div className="slip-overlay" onClick={() => setMobileSlipOpen(false)} />}

        <button className="slip-fab" onClick={() => setMobileSlipOpen(true)}>
          📝
          {slip.length > 0 && <span className="slip-fab-count">{slip.length}</span>}
        </button>
      </div>
    </div>
  )
}
