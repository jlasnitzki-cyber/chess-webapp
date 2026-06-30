export default function Sidebar({
  currentTurn,
  playerColor,
  engineColor,
  thinking,
  gameOver,
  gameOverReason,
  winner,
  evalScore,
  timeLimitMs,
  botLimitMode,
  depthLimit,
  onTimeLimitChange,
  onDepthLimitChange,
  onBotLimitModeChange,
  onNewGame,
  onUndo,
  onPlayerColorChange
}) {
  let status
  if (gameOver) {
    status =
      gameOverReason === 'checkmate'
        ? `Checkmate - ${winner} wins`
        : 'Stalemate - draw'
  } else if (thinking) {
    status = 'Engine is thinking...'
  } else {
    status = `${currentTurn === 'white' ? 'White' : 'Black'} to move`
  }

  return (
    <div className="sidebar">
      <div className="panel status-panel">
        <h2>Status</h2>
        <p className={gameOver ? 'status-over' : 'status-line'}>{status}</p>
        <p className="muted">
          You: {playerColor} | Engine: {engineColor}
        </p>
        <p className="muted">Eval: {evalScore > 0 ? `+${evalScore}` : evalScore}</p>
      </div>

      <div className="panel controls-panel">
        <h2>Controls</h2>
        <div className="color-picker" aria-label="Choose player color">
          <button
            className={`segmented-btn ${playerColor === 'white' ? 'active' : ''}`}
            onClick={() => onPlayerColorChange('white')}
            disabled={thinking}
            type="button"
          >
            White
          </button>
          <button
            className={`segmented-btn ${playerColor === 'black' ? 'active' : ''}`}
            onClick={() => onPlayerColorChange('black')}
            disabled={thinking}
            type="button"
          >
            Black
          </button>
        </div>
        <button className="btn" onClick={onNewGame} disabled={thinking}>
          New game
        </button>
        <button className="btn" onClick={onUndo} disabled={thinking}>
          Undo
        </button>
        <div className="time-label">
          Engine limit
          <div className="limit-picker" aria-label="Choose engine limit mode">
            <button
              className={`segmented-btn ${botLimitMode === 'time' ? 'active' : ''}`}
              onClick={() => onBotLimitModeChange('time')}
              disabled={thinking}
              type="button"
            >
              Time
            </button>
            <button
              className={`segmented-btn ${botLimitMode === 'depth' ? 'active' : ''}`}
              onClick={() => onBotLimitModeChange('depth')}
              disabled={thinking}
              type="button"
            >
              Depth
            </button>
          </div>
        </div>

        <label className={`time-label ${botLimitMode !== 'time' ? 'inactive-setting' : ''}`}>
          Move time: {(timeLimitMs / 1000).toFixed(1)}s
          <input
            type="range"
            min="100"
            max="10000"
            step="100"
            value={timeLimitMs}
            onChange={(e) => onTimeLimitChange(Number(e.target.value))}
            disabled={thinking || botLimitMode !== 'time'}
          />
        </label>

        <label className={`time-label ${botLimitMode !== 'depth' ? 'inactive-setting' : ''}`}>
          Search depth: {depthLimit}
          <input
            type="range"
            min="1"
            max="6"
            step="1"
            value={depthLimit}
            onChange={(e) => onDepthLimitChange(Number(e.target.value))}
            disabled={thinking || botLimitMode !== 'depth'}
          />
        </label>
      </div>

    </div>
  )
}
