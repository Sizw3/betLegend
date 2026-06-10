export default function BetSlip({ slip, onRemove, onClear, onBuildSlip, analyzing }) {
    const analyzedGames = slip.filter(s => s.prediction && !s.prediction.error)
    const unanalyzedGames = slip.filter(s => !s.prediction)

    const rawProb = analyzedGames.length > 0
        ? analyzedGames.reduce((acc, item) => acc * (parseFloat(item.prediction.confidence) / 100), 1) * 100
        : 0

    const totalConfidence = isNaN(rawProb) ? 0 : rawProb.toFixed(1)

    return (
        <div className="bet-slip">
            <div className="slip-header">
                <span>BET SLIP</span>
                <span className="slip-count">{slip.length}</span>
            </div>

            <div className="slip-content">
                {slip.length === 0 ? (
                    <div className="empty-slip">
                        <div className="empty-icon">📝</div>
                        <p>Your slip is empty</p>
                        <span>Explorer matches and click "Add to Slip"</span>
                    </div>
                ) : (
                    <>
                        {slip.map((item, index) => (
                            <div key={index} className={`slip-item slide-up ${!item.prediction ? 'pending' : ''}`}>
                                <button className="remove-item" onClick={() => onRemove(index)}>×</button>
                                <div className="slip-item-teams">
                                    {item.home} vs {item.away}
                                </div>

                                {item.prediction ? (
                                    item.prediction.error ? (
                                        <div className="slip-pending" style={{ color: 'var(--red)' }}>
                                            ⚠️ Error: {item.prediction.error.length > 30 ? item.prediction.error.substring(0, 27) + '...' : item.prediction.error}
                                        </div>
                                    ) : (
                                        <>
                                            <div className="slip-item-pick">
                                                <span className="pick-label">Pick:</span>
                                                <span className="pick-value">{item.prediction.recommendation}</span>
                                            </div>
                                            <div className="slip-item-meta">
                                                <span className="slip-market">{item.prediction.betway_market}</span>
                                                <span className="slip-conf">{item.prediction.confidence}% Conf.</span>
                                            </div>
                                        </>
                                    )
                                ) : (
                                    <div className="slip-pending">
                                        <span className="loading-pulse">🔍 Awaiting Analysis...</span>
                                    </div>
                                )}
                            </div>
                        ))}
                    </>
                )}
            </div>

            {slip.length > 0 && (
                <div className="slip-footer">
                    {analyzedGames.length > 0 && (
                        <div className="slip-summary">
                            <div className="summary-row">
                                <span>Combined Prob.</span>
                                <span className="highlight-green">{totalConfidence}%</span>
                            </div>
                        </div>
                    )}

                    <button
                        className="place-bet-btn"
                        onClick={onBuildSlip}
                        disabled={analyzing || unanalyzedGames.length === 0}
                        style={{ opacity: unanalyzedGames.length === 0 ? 0.6 : 1 }}
                    >
                        {analyzing ? '⚡ BUILDING SLIP...' : 'RUN MULTI-ANALYSIS 🚀'}
                    </button>

                    {analyzedGames.length > 0 && <button className="clear-slip-link" onClick={onClear}>Clear All & Reset</button>}
                </div>
            )}
        </div>
    )
}
