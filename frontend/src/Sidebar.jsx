import { pieceGlyph } from './pieces.js'

function MoveHistory({ moveLog }) {
  const rows = []
  for (let i = 0; i < moveLog.length; i += 2) {
    rows.push({
      number: i / 2 + 1,
      white: moveLog[i],
      black: moveLog[i + 1]
    })
  }

  return (
    <div className="panel">
      <h2>Moves</h2>
      <div className="move-history">
        {rows.length === 0 && <p className="muted">No moves yet</p>}
        {rows.map((r) => (
          <div className="move-row" key={r.number}>
            <span className="move-number">{r.number}.</span>
            <span className="move-white">{r.white}</span>
            <span className="move-black">{r.black || ''}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function CapturedRow({ label, pieces }) {
  return (
    <div className="captured-row">
      <span className="muted">{label}</span>
      <span className="captured-glyphs">
        {pieces.map((p, i) => (
          <span key={i}>{pieceGlyph(p)}</span>
        ))}
      </span>
    </div>
  )
}

export default function Sidebar({
  currentTurn,
  thinking,
  gameOver,
  gameOverReason,
  winner,
  evalScore,
  depth,
  onDepthChange,
  onNewGame,
  onUndo,
  moveLog,
  capturedPieces
}) {
  let status
  if (gameOver) {
    status =
      gameOverReason === 'checkmate'
        ? `Checkmate — ${winner} wins`
        : 'Stalemate — draw'
  } else if (thinking) {
    status = 'Engine is thinking…'
  } else {
    status = `${currentTurn === 'white' ? 'White' : 'Black'} to move`
  }

  return (
    <div className="sidebar">
      <div className="panel status-panel">
        <h2>Status</h2>
        <p className={gameOver ? 'status-over' : 'status-line'}>{status}</p>
        <p className="muted">Eval: {evalScore > 0 ? `+${evalScore}` : evalScore}</p>
      </div>

      <div className="panel controls-panel">
        <h2>Controls</h2>
        <button className="btn" onClick={onNewGame}>
          New game
        </button>
        <button className="btn" onClick={onUndo} disabled={thinking}>
          Undo
        </button>
        <label className="depth-label">
          Engine depth: {depth}
          <input
            type="range"
            min="1"
            max="5"
            value={depth}
            onChange={(e) => onDepthChange(Number(e.target.value))}
            disabled={thinking}
          />
        </label>
      </div>

      <div className="panel">
        <h2>Captured</h2>
        <CapturedRow label="By white" pieces={capturedPieces.white} />
        <CapturedRow label="By black" pieces={capturedPieces.black} />
      </div>

      <MoveHistory moveLog={moveLog} />
    </div>
  )
}
