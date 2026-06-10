import { useState, useEffect } from 'react'
import { API_BASE_URL } from '../config'

export default function MatchExplorer({ onAddToSlip }) {
    const [matches, setMatches] = useState([])
    const [loading, setLoading] = useState(true)
    const [offset, setOffset] = useState(0)
    const [searchTerm, setSearchTerm] = useState('')
    const [selectedLeague, setSelectedLeague] = useState('All')

    const fetchMatches = async () => {
        setLoading(true)
        try {
            const res = await fetch(`${API_BASE_URL}/api/sportdb/football?offset=${offset}`)
            if (res.ok) {
                setMatches(await res.json())
            }
        } catch (e) {
            console.error("Fetch error", e)
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        fetchMatches()
    }, [offset])

    const filteredMatches = matches.filter(m => {
        const s = searchTerm.toLowerCase()
        const matchesSearch = m.homeName.toLowerCase().includes(s) ||
            m.awayName.toLowerCase().includes(s) ||
            m.tournamentName.toLowerCase().includes(s)
        const matchesLeague = selectedLeague === 'All' || m.tournamentName === selectedLeague
        return matchesSearch && matchesLeague
    })

    const uniqueLeagues = ['All', ...new Set(matches.map(m => m.tournamentName))]

    const groupedMatches = filteredMatches.reduce((acc, m) => {
        if (!acc[m.tournamentName]) acc[m.tournamentName] = []
        acc[m.tournamentName].push(m)
        return acc
    }, {})

    const getDateLabel = (d) => {
        if (d === -1) return 'Yesterday'
        if (d === 0) return 'Live'
        if (d === 1) return 'Tomorrow'
        const date = new Date()
        date.setDate(date.getDate() + d)
        return new Intl.DateTimeFormat('en-US', { weekday: 'short', day: 'numeric' }).format(date)
    }

    return (
        <div className="card" style={{ display: 'flex', flexDirection: 'column', maxHeight: '800px', marginBottom: 0 }}>
            {/* Header & Date Toggle */}
            <div className="ranked-title" style={{ display: 'flex', flexDirection: 'column', gap: '.8rem', marginBottom: '1.2rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span>⚽ Match Explorer</span>
                    <span style={{ fontSize: '.6rem', color: 'var(--green)' }}>SPORTDB LIVE FEED</span>
                </div>
                <div className="date-toggle" style={{ width: '100%' }}>
                    {[-1, 0, 1, 2, 3, 4].map(d => (
                        <button
                            key={d}
                            className={`date-btn ${offset === d ? 'active' : ''}`}
                            onClick={() => setOffset(d)}
                            style={{ flex: 1, fontSize: '.6rem' }}
                        >
                            {getDateLabel(d)}
                        </button>
                    ))}
                </div>
            </div>

            {/* Search & Filters */}
            <input
                type="text"
                placeholder="Search teams or leagues..."
                className="form-input"
                value={searchTerm}
                onChange={e => setSearchTerm(e.target.value)}
                style={{ marginBottom: '1rem', background: 'rgba(0,0,0,0.3)' }}
            />

            <div className="league-chips" style={{ overflowX: 'auto', flexWrap: 'nowrap', paddingBottom: '.8rem' }}>
                {uniqueLeagues.map(l => (
                    <button
                        key={l}
                        className={`chip-btn ${selectedLeague === l ? 'active' : ''}`}
                        onClick={() => setSelectedLeague(l)}
                    >
                        {l}
                    </button>
                ))}
            </div>

            {/* Results List */}
            <div className="live-matches-grid" style={{ flex: 1, overflowY: 'auto' }}>
                {loading ? (
                    <div className="loading-pulse" style={{ padding: '2rem', textAlign: 'center' }}>⚡ Discovering Matches...</div>
                ) : Object.keys(groupedMatches).length === 0 ? (
                    <div style={{ color: 'var(--muted)', textAlign: 'center', padding: '2rem' }}>No matches found for this date.</div>
                ) : (
                    Object.entries(groupedMatches).map(([tournament, leagueMatches]) => (
                        <div key={tournament} style={{ marginBottom: '1.2rem' }}>
                            <div className="match-category" style={{ fontSize: '.65rem', marginBottom: '.5rem' }}>{tournament}</div>
                            {leagueMatches.map((m, i) => (
                                <div key={m.eventId || i} className="live-match-card" style={{ marginBottom: '.5rem' }}>
                                    <div className="live-match-meta">
                                        <span className="live-timer" style={{ color: m.eventStageId === "2" ? 'var(--green)' : 'var(--muted)' }}>
                                            {m.eventStageId === "2" ? `${m.gameTime}'` : m.startTime}
                                        </span>
                                        <span className="live-stage">{m.eventStage}</span>
                                    </div>
                                    <div className="live-teams" style={{ marginBottom: '.8rem' }}>
                                        <div className="live-team-row">
                                            <span>{m.homeName}</span>
                                            <span className="live-score">{m.homeScore ?? '-'}</span>
                                        </div>
                                        <div className="live-team-row">
                                            <span>{m.awayName}</span>
                                            <span className="live-score">{m.awayScore ?? '-'}</span>
                                        </div>
                                    </div>
                                    <button
                                        className="quick-analyze-btn"
                                        style={{ background: 'rgba(0,255,136,0.1)', borderColor: 'var(--green)', color: 'var(--green)' }}
                                        onClick={() => onAddToSlip({ home: m.homeName, away: m.awayName })}
                                    >
                                        Add to Slip 📑
                                    </button>
                                </div>
                            ))}
                        </div>
                    ))
                )}
            </div>
        </div>
    )
}
