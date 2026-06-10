import { useState, useEffect } from 'react'
import './index.css'

const MODE_META = {
  low_risk:     { label: '🛡️ Low Risk',     short: 'Low Risk',     desc: 'Only near-certain outcomes. Extreme safety nets.', btnClass: 'btn-low',  badgeClass: 'badge-low',  fillClass: 'fill-low',  activeBtnClass: 'active-low'  },
  conservative: { label: '⚖️ Conservative', short: 'Conservative', desc: 'Balanced. High-confidence markets.', btnClass: 'btn-cons', badgeClass: 'badge-cons', fillClass: 'fill-cons', activeBtnClass: 'active-cons' },
  high_risk:    { label: '🔥 High Risk',    short: 'High Risk',    desc: 'Higher odds. Straight wins, BTTS. For the bold.', btnClass: 'btn-high', badgeClass: 'badge-high', fillClass: 'fill-high', activeBtnClass: 'active-high' },
}

function StatCell({ label, value, highlight }) {
  return (
    <div className="stat-cell" style={highlight ? { border: '1px solid rgba(0,255,136,.3)' } : {}}>
      <div className="stat-cell-label">{label}</div>
      <div className="stat-cell-value" style={highlight ? { color: 'var(--green)' } : {}}>{value}</div>
    </div>
  )
}

function MlBar({ label, value }) {
  const pct = Math.round(value)
  const color = pct >= 65 ? 'var(--green)' : pct >= 50 ? 'var(--blue)' : 'var(--muted)'
  return (
    <div style={{ marginBottom: '.5rem' }}>
      <div style={{ display:'flex', justifyContent:'space-between', fontSize:'.75rem', marginBottom:'.2rem' }}>
        <span style={{ color:'var(--muted)' }}>{label}</span>
        <span style={{ fontWeight:700, color }}>{pct}%</span>
      </div>
      <div className="conf-bar-bg" style={{ marginBottom:0 }}>
        <div style={{ height:'100%', width:`${pct}%`, background:color, borderRadius:99, transition:'width .6s ease' }} />
      </div>
    </div>
  )
}

// ── Mini equity chart ─────────────────────────────────────────
function EquityChart({ data, stake }) {
  if (!data || data.length < 2) return null
  const w = 600, h = 140, pad = 20
  const min = Math.min(...data), max = Math.max(...data)
  const range = max - min || 1
  const pts = data.map((v, i) => {
    const x = pad + (i / (data.length - 1)) * (w - pad * 2)
    const y = pad + ((max - v) / range) * (h - pad * 2)
    return `${x},${y}`
  }).join(' ')
  const color = data[data.length-1] >= 0 ? '#00ff88' : '#ff3b5c'
  return (
    <svg viewBox={`0 0 ${w} ${h}`} style={{ width:'100%', height:'auto', marginBottom:'1rem' }}>
      <defs>
        <linearGradient id="ec" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.3"/>
          <stop offset="100%" stopColor={color} stopOpacity="0.0"/>
        </linearGradient>
      </defs>
      <line x1={pad} y1={pad} x2={pad} y2={h-pad} stroke="rgba(255,255,255,.06)" strokeWidth="1"/>
      <line x1={pad} y1={h-pad} x2={w-pad} y2={h-pad} stroke="rgba(255,255,255,.06)" strokeWidth="1"/>
      <polyline points={pts} fill="none" stroke={color} strokeWidth="2.5" strokeLinejoin="round"/>
      <text x={pad+4} y={pad+12} fill="rgba(255,255,255,.4)" fontSize="10">+R{Math.round(max)}</text>
      <text x={pad+4} y={h-pad-4} fill="rgba(255,255,255,.4)" fontSize="10">{Math.round(min) < 0 ? `-R${Math.abs(Math.round(min))}` : `R${Math.round(min)}`}</text>
    </svg>
  )
}

// ── Backtest Tab ──────────────────────────────────────────────
function BacktestTab() {
  const [mode, setMode] = useState('conservative')
  const [stake, setStake] = useState('10')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [showAll, setShowAll] = useState(false)

  const runTest = async () => {
    setLoading(true); setError(null); setResult(null)
    try {
      const res = await fetch('http://localhost:8000/api/backtest', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ mode, stake: parseFloat(stake) })
      })
      if (!res.ok) throw new Error('Backtest failed')
      setResult(await res.json())
    } catch(e) { setError(e.message) }
    finally { setLoading(false) }
  }

  const meta = MODE_META[mode]
  const displayed = result ? (showAll ? result.recent_results : result.recent_results.slice(-20)) : []

  return (
    <div className="card slide-up">
      <div style={{ marginBottom:'1.2rem' }}>
        <div className="ranked-title" style={{ marginBottom:'.7rem' }}>Select Mode to Backtest</div>
        <div className="mode-toggle">
          {Object.entries(MODE_META).map(([key,m]) => (
            <button key={key} className={`mode-btn ${mode===key ? m.activeBtnClass : ''}`} onClick={() => setMode(key)}>{m.label}</button>
          ))}
        </div>
        <div className="field" style={{ marginBottom:'1rem' }}>
          <label>Flat Stake Per Bet (R)</label>
          <input type="number" min="1" max="1000" value={stake} onChange={e => setStake(e.target.value)} className="form-input"/>
        </div>
        <button className={`analyze-btn ${meta.btnClass}`} onClick={runTest} disabled={loading}>
          {loading ? <span className="loading-pulse">⏳ Running 1,400+ Historical Matches...</span> : '▶ Run Backtest'}
        </button>
        {error && <p className="error-msg">{error}</p>}
      </div>

      {result && (
        <>
          {/* Summary KPIs */}
          <div className="stats-grid" style={{ marginBottom:'1rem' }}>
            <StatCell label="Total Matches"  value={result.total_matches} />
            <StatCell label="Bets Placed"    value={result.bets_placed} />
            <StatCell label="Win Rate"        value={`${result.win_rate_pct}%`} highlight={result.win_rate_pct >= 70} />
            <StatCell label="Net P&L"         value={`R${result.net_pnl}`} highlight={result.net_pnl > 0} />
            <StatCell label="ROI"             value={`${result.roi_pct}%`} highlight={result.roi_pct > 0} />
            <StatCell label="Bets Skipped"   value={result.bets_skipped} />
          </div>

          {/* Equity Curve */}
          <div className="ranked-title">Equity Curve (Last {result.equity_curve.length} bets @ R{stake}/bet)</div>
          <div style={{ background:'rgba(0,0,0,.3)', borderRadius:10, padding:'1rem', marginBottom:'1.2rem' }}>
            <EquityChart data={result.equity_curve} stake={parseFloat(stake)} />
          </div>

          {/* Market Breakdown */}
          <div className="ranked-title">Performance by Market</div>
          {result.market_breakdown.map((m, i) => (
            <div key={i} className={`ranked-item ${i===0 ? 'top' : ''}`} style={{ flexWrap:'wrap', gap:'.4rem' }}>
              <span style={{ flex:1 }}>{i===0?'⭐ ':''}{m.market}</span>
              <span style={{ color:'var(--muted)', fontSize:'.75rem' }}>{m.wins}/{m.total} ({m.win_rate}%)</span>
              <span className="ranked-conf" style={{ color: m.pnl >= 0 ? 'var(--green)' : 'var(--red)' }}>R{m.pnl}</span>
            </div>
          ))}

          {/* Recent Results */}
          <div className="ranked-title" style={{ marginTop:'1.5rem' }}>
            Recent Match Results ({showAll ? 'All 50' : 'Last 20'})
          </div>
          <div style={{ overflowX:'auto' }}>
            <table style={{ width:'100%', fontSize:'.75rem', borderCollapse:'collapse' }}>
              <thead>
                <tr style={{ color:'var(--muted)', borderBottom:'1px solid var(--border)' }}>
                  <th style={{ textAlign:'left', padding:'.4rem' }}>Match</th>
                  <th style={{ padding:'.4rem' }}>Predicted</th>
                  <th style={{ padding:'.4rem' }}>Conf</th>
                  <th style={{ padding:'.4rem' }}>Result</th>
                  <th style={{ padding:'.4rem' }}>✓</th>
                  <th style={{ padding:'.4rem' }}>P&L</th>
                  <th style={{ padding:'.4rem' }}>Balance</th>
                </tr>
              </thead>
              <tbody>
                {displayed.map((r, i) => (
                  <tr key={i} style={{ borderBottom:'1px solid var(--border)', opacity: r.won ? 1 : 0.6 }}>
                    <td style={{ padding:'.4rem', color:'var(--text)' }}>{r.match}</td>
                    <td style={{ padding:'.4rem', textAlign:'center', fontSize:'.7rem', color:'var(--blue)' }}>{r.predicted_market.replace(/_/g,' ')}</td>
                    <td style={{ padding:'.4rem', textAlign:'center' }}>{r.confidence}%</td>
                    <td style={{ padding:'.4rem', textAlign:'center', fontWeight:700 }}>{r.result}</td>
                    <td style={{ padding:'.4rem', textAlign:'center' }}>{r.won ? '✅' : '❌'}</td>
                    <td style={{ padding:'.4rem', textAlign:'center', color: r.pnl >= 0 ? 'var(--green)' : 'var(--red)', fontWeight:700 }}>R{r.pnl}</td>
                    <td style={{ padding:'.4rem', textAlign:'center', color:'var(--muted)' }}>R{r.balance}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <button className="reset-btn" style={{ marginTop:'1rem' }} onClick={() => setShowAll(!showAll)}>
            {showAll ? 'Show Less' : 'Show All 50 Results'}
          </button>
        </>
      )}
    </div>
  )
}

// ── Analyze Tab ───────────────────────────────────────────────
function AnalyzeTab() {
  const [homeTeam, setHomeTeam] = useState('')
  const [awayTeam, setAwayTeam] = useState('')
  const [mode, setMode] = useState('low_risk')
  const [odds, setOdds] = useState('')
  const [prediction, setPrediction] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [upcomingMatches, setUpcomingMatches] = useState([])
  const [matchSearch, setMatchSearch] = useState('')
  const [selectedLeague, setSelectedLeague] = useState('All')
  const [loadingUpcoming, setLoadingUpcoming] = useState(false)

  useEffect(() => {
    async function fetchUpcoming() {
      setLoadingUpcoming(true)
      try {
        const res = await fetch('http://localhost:8000/api/upcoming')
        if (res.ok) {
          const data = await res.json()
          setUpcomingMatches(data)
        }
      } catch (err) {
        console.error("Failed to load upcoming matches", err)
      } finally {
        setLoadingUpcoming(false)
      }
    }
    fetchUpcoming()
  }, [])

  const selectMatch = (h, a) => {
    setHomeTeam(h)
    setAwayTeam(a)
    setMatchSearch('') // optionally clear search
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const uniqueLeagues = ['All', ...new Set(upcomingMatches.map(m => m.tournament))]

  const filteredMatches = upcomingMatches.filter(m => {
    const matchesSearch = 
      m.home_team.toLowerCase().includes(matchSearch.toLowerCase()) || 
      m.away_team.toLowerCase().includes(matchSearch.toLowerCase()) ||
      m.tournament.toLowerCase().includes(matchSearch.toLowerCase());
    
    const matchesLeague = selectedLeague === 'All' || m.tournament === selectedLeague;
    
    return matchesSearch && matchesLeague;
  })

  // Group by tournament
  const groupedMatches = filteredMatches.reduce((acc, m) => {
    if (!acc[m.tournament]) acc[m.tournament] = []
    acc[m.tournament].push(m)
    return acc
  }, {})

  const analyze = async (e) => {
    e.preventDefault(); setLoading(true); setError(null); setPrediction(null)
    try {
      const body = { home_team: homeTeam, away_team: awayTeam, mode }
      if (odds) body.betway_odds = parseFloat(odds)
      const res = await fetch('http://localhost:8000/api/analyze', {
        method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)
      })
      if (!res.ok) throw new Error('Backend error. Is server running?')
      setPrediction(await res.json())
    } catch(err) { setError(err.message) }
    finally { setLoading(false) }
  }

  const reset = () => { setPrediction(null); setHomeTeam(''); setAwayTeam(''); setOdds('') }
  const meta = MODE_META[mode]

  const rightPanelContent = prediction ? (
    <div className="card slide-up" style={{ marginBottom: 0 }}>
      <span className={`pred-badge ${meta.badgeClass}`}>{meta.short} Mode</span>
      <div className="pred-matchup">{prediction.stats_summary.home?.name}<span className="pred-vs">vs</span>{prediction.stats_summary.away?.name}</div>
      <div className="pred-pick">{prediction.recommendation}</div>
      <div className="pred-betway">Betway → {prediction.betway_market}</div>
      {prediction.edge != null && (
        <div className={`edge-badge ${prediction.edge > 0 ? 'edge-positive' : 'edge-negative'}`}>
          {prediction.edge > 0 ? `✅ Positive EV: +${(prediction.edge*100).toFixed(1)}%` : `⚠️ Negative EV: ${(prediction.edge*100).toFixed(1)}%`}
        </div>
      )}
      <div className="confidence-row"><span className="conf-label">Confidence</span><span className="conf-value">{prediction.confidence}%</span></div>
      <div className="conf-bar-bg"><div className={`conf-bar-fill ${meta.fillClass}`} style={{ width:`${prediction.confidence}%` }}/></div>
      {prediction.ml_probabilities && Object.keys(prediction.ml_probabilities).length > 0 && (
        <><div className="ranked-title" style={{ marginBottom:'.7rem' }}>XGBoost ML Probabilities (5,330 Matches Trained)</div>
        <div style={{ marginBottom:'1.5rem' }}>
          {Object.entries(prediction.ml_probabilities).map(([k,v]) => (
            <MlBar key={k} label={k.replace(/_/g,' ').replace(/\b\w/g,l=>l.toUpperCase())} value={v}/>
          ))}
        </div></>
      )}
      {prediction.stats_summary.home && (
        <><div className="ranked-title">{prediction.stats_summary.home.name} — Last {prediction.stats_summary.home.matches_analyzed} Matches</div>
        <div className="stats-grid" style={{ marginBottom:'1rem' }}>
          <StatCell label="Avg Goals/Game" value={prediction.stats_summary.home.avg_total_goals}/>
          <StatCell label="Avg Scored" value={prediction.stats_summary.home.avg_scored}/>
          <StatCell label="Avg Conceded" value={prediction.stats_summary.home.avg_conceded}/>
          <StatCell label="Win Rate" value={`${Math.round(prediction.stats_summary.home.win_rate*100)}%`}/>
          <StatCell label="BTTS Rate" value={`${Math.round(prediction.stats_summary.home.btts_rate*100)}%`}/>
          <StatCell label="Clean Sheets" value={`${Math.round(prediction.stats_summary.home.clean_sheet_rate*100)}%`}/>
        </div></>
      )}
      {prediction.stats_summary.away && (
        <><div className="ranked-title">{prediction.stats_summary.away.name} — Last {prediction.stats_summary.away.matches_analyzed} Matches</div>
        <div className="stats-grid">
          <StatCell label="Avg Goals/Game" value={prediction.stats_summary.away.avg_total_goals}/>
          <StatCell label="Avg Scored" value={prediction.stats_summary.away.avg_scored}/>
          <StatCell label="Avg Conceded" value={prediction.stats_summary.away.avg_conceded}/>
          <StatCell label="Win Rate" value={`${Math.round(prediction.stats_summary.away.win_rate*100)}%`}/>
          <StatCell label="BTTS Rate" value={`${Math.round(prediction.stats_summary.away.btts_rate*100)}%`}/>
          <StatCell label="Clean Sheets" value={`${Math.round(prediction.stats_summary.away.clean_sheet_rate*100)}%`}/>
        </div></>
      )}
      {prediction.stats_summary.h2h && (
        <div className="h2h-block" style={{ marginTop:'1rem' }}>
          <div className="h2h-title">H2H — Last {prediction.stats_summary.h2h.matches_analyzed} Meetings</div>
          <div className="h2h-row"><span>Avg Goals</span><strong>{prediction.stats_summary.h2h.avg_total_goals}</strong></div>
          <div className="h2h-row"><span>BTTS Rate</span><strong>{Math.round(prediction.stats_summary.h2h.btts_rate*100)}%</strong></div>
          <div className="h2h-row"><span>Over 2.5</span><strong>{Math.round(prediction.stats_summary.h2h.over_2_5_rate*100)}%</strong></div>
          <div className="h2h-row"><span>Under 3.5</span><strong>{Math.round(prediction.stats_summary.h2h.under_3_5_rate*100)}%</strong></div>
        </div>
      )}

      {/* Intelligence Layer */}
      {prediction.intelligence && prediction.intelligence.home_squad_rating && (
        <div className="h2h-block" style={{ marginTop:'1rem', borderColor:'rgba(0,255,136,.15)', background:'rgba(0,255,136,.03)' }}>
          <div className="h2h-title" style={{ color:'var(--green)' }}>🧠 Intelligence Layer — Squad + Formation + FIFA Rank</div>
          <div className="h2h-row">
            <span>Squad Ratings</span>
            <strong>{prediction.intelligence.home_squad_rating?.toFixed(2)} vs {prediction.intelligence.away_squad_rating?.toFixed(2)}</strong>
          </div>
          <div className="h2h-row">
            <span>Top Player Ratings</span>
            <strong>{prediction.intelligence.home_top_player?.toFixed(2)} vs {prediction.intelligence.away_top_player?.toFixed(2)}</strong>
          </div>
          <div className="h2h-row">
            <span>Formations</span>
            <strong>{prediction.intelligence.home_formation} vs {prediction.intelligence.away_formation}</strong>
          </div>
          <div className="h2h-row">
            <span>FIFA World Rankings</span>
            <strong>#{prediction.intelligence.home_fifa_rank} vs #{prediction.intelligence.away_fifa_rank}</strong>
          </div>
          <div className="h2h-row">
            <span>Squad Quality Gap</span>
            <strong style={{ color: prediction.intelligence.squad_quality_gap > 0 ? 'var(--green)' : prediction.intelligence.squad_quality_gap < 0 ? 'var(--red)' : 'var(--muted)' }}>
              {prediction.intelligence.squad_quality_gap > 0 ? '+' : ''}{prediction.intelligence.squad_quality_gap?.toFixed(2)} (Home favoured)
            </strong>
          </div>
          <div className="h2h-row">
            <span>Combined Strength Signal</span>
            <strong style={{ color: prediction.intelligence.strength_signal > 0.2 ? 'var(--green)' : prediction.intelligence.strength_signal < -0.2 ? 'var(--red)' : 'var(--muted)' }}>
              {prediction.intelligence.strength_signal > 0 ? '+' : ''}{prediction.intelligence.strength_signal?.toFixed(3)}
            </strong>
          </div>
        </div>
      )}

      <div className="ranked-title" style={{ marginTop:'1.5rem' }}>All Ranked Markets</div>
      {prediction.ranked_markets.map((m,i) => (
        <div key={i} className={`ranked-item ${i===0?'top':''}`}>
          <span>{i===0?'⭐ ':''}{m.market}</span>
          <span className="ranked-conf">{m.confidence_pct}%</span>
        </div>
      ))}
      <p style={{ fontSize:'.78rem', color:'var(--muted)', marginTop:'1rem', lineHeight:1.6 }}>
        <strong style={{ color:'var(--text)' }}>Rationale:</strong> {prediction.rationale}
      </p>
      <button className="reset-btn" onClick={reset}>← Analyze Another Match</button>
    </div>
  ) : (
    <div className="card" style={{ marginBottom: 0 }}>
      <div className="mode-toggle">
        {Object.entries(MODE_META).map(([key,m]) => (
          <button key={key} className={`mode-btn ${mode===key?m.activeBtnClass:''}`} onClick={()=>setMode(key)}>{m.label}</button>
        ))}
      </div>
      <div className="ranked-title" style={{ marginTop:'1rem', marginBottom:'.7rem' }}>Match Details</div>
      <form onSubmit={analyze}>
        <div className="input-row">
          <div className="field"><label>Home Team</label>
            <input type="text" placeholder="e.g. Real Madrid" value={homeTeam} onChange={e=>setHomeTeam(e.target.value)} required/>
          </div>
          <div className="field"><label>Away Team</label>
            <input type="text" placeholder="e.g. Barcelona" value={awayTeam} onChange={e=>setAwayTeam(e.target.value)} required/>
          </div>
        </div>
        <div className="field" style={{ marginBottom:'1rem' }}>
          <label>Betway Odds (optional — for EV edge detection)</label>
          <input type="number" step="0.01" min="1.01" placeholder="e.g. 1.75" value={odds} onChange={e=>setOdds(e.target.value)}/>
        </div>
        <button type="submit" className={`analyze-btn ${meta.btnClass}`} disabled={loading || !homeTeam || !awayTeam}>
          {loading ? <span className="loading-pulse">⏳ Scraping Sofascore + Running XGBoost...</span> : `Analyze — ${meta.label}`}
        </button>
        {error && <p className="error-msg">{error}</p>}
      </form>
      <p className="mode-desc">{meta.desc}</p>
    </div>
  )

  return (
    <div className="dashboard-layout slide-up">
      <div className="card" style={{ padding: '1.2rem', marginBottom: 0, display: 'flex', flexDirection: 'column', maxHeight: '800px' }}>
        <div className="ranked-title" style={{ marginBottom:'.8rem' }}>Live Upcoming Matches</div>
        <input 
          type="text" 
          placeholder="Filter by team or league..." 
          value={matchSearch} 
          onChange={e => setMatchSearch(e.target.value)} 
          className="form-input"
          style={{ width: '100%', background: 'rgba(0,0,0,0.4)', border: '1px solid var(--border)', borderRadius: '8px', padding: '.6rem .8rem', color: 'var(--text)', marginBottom: '1rem', outline: 'none' }}
        />
        
        <div className="league-chips" style={{ overflowX: 'auto', flexWrap: 'nowrap', paddingBottom: '.5rem', marginBottom: '.5rem', WebkitOverflowScrolling: 'touch' }}>
          {uniqueLeagues.map(l => (
            <button 
              key={l} 
              className={`chip-btn ${selectedLeague === l ? 'active' : ''}`}
              onClick={() => setSelectedLeague(l)}
              style={{ flexShrink: 0 }}
            >
              {l.length > 25 ? l.substring(0, 22) + '...' : l}
            </button>
          ))}
        </div>
        
        <div style={{ overflowY: 'auto', flex: 1, paddingRight: '.3rem' }}>
          {loadingUpcoming ? (
            <div style={{ fontSize:'.8rem', color:'var(--muted)', textAlign:'center', padding:'2rem 0' }}>⏳ Loading matches...</div>
          ) : Object.keys(groupedMatches).length === 0 ? (
            <div style={{ fontSize:'.8rem', color:'var(--muted)', textAlign:'center', padding:'2rem 0' }}>No matches found.</div>
          ) : (
            Object.entries(groupedMatches).map(([tournament, matches]) => (
              <div key={tournament} style={{ marginBottom: '1rem' }}>
                <div className="match-category">{tournament}</div>
                {matches.map((m, i) => (
                  <div 
                    key={i} 
                    className="match-item"
                    onClick={() => selectMatch(m.home_team, m.away_team)}
                  >
                    <div className="match-item-teams">{m.home_team} <span style={{color:'var(--muted)', fontWeight:400, fontSize:'.7rem'}}>vs</span> {m.away_team}</div>
                  </div>
                ))}
              </div>
            ))
          )}
        </div>
      </div>
      
      <div className="main-panel">
        {rightPanelContent}
      </div>
    </div>
  )
}

// ── App Shell ─────────────────────────────────────────────────
export default function App() {
  const [tab, setTab] = useState('analyze')

  return (
    <div id="root">
      <header className="header">
        <div className="header-logo">Bet Legend</div>
        <div className="header-sub">XGBoost AI · Evolutionary Engine · Betway Compatible</div>
      </header>

      <div className="tab-bar">
        <button className={`tab-btn ${tab==='analyze'?'tab-active':''}`} onClick={()=>setTab('analyze')}>🔍 Analyze Match</button>
        <button className={`tab-btn ${tab==='backtest'?'tab-active':''}`} onClick={()=>setTab('backtest')}>📊 Backtest Results</button>
      </div>

      {tab === 'analyze' ? <AnalyzeTab /> : <BacktestTab />}
    </div>
  )
}
