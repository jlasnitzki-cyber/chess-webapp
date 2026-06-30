import { useEffect, useState } from 'react'
import Board from './Board.jsx'
import Sidebar from './Sidebar.jsx'
import { pieceGlyph } from './pieces.js'
import {
  getState,
  newGame,
  getLegalMoves,
  makeMove,
  undoMove,
  setBotLimit
} from './api.js'

const EMPTY_BOARD = Array.from({ length: 8 }, () => Array(8).fill(0))
const PIECE_VALUES = { 1: 0, 2: 9, 3: 3, 4: 3, 5: 5, 6: 1 }

function materialTotal(pieces) {
  return pieces.reduce((sum, piece) => sum + PIECE_VALUES[Math.abs(piece)], 0)
}

function CapturedStrip({ label, pieces }) {
  return (
    <div className="captured-strip">
      <div className="captured-strip-heading">
        <span>{label}</span>
        <span>+{materialTotal(pieces)}</span>
      </div>
      <div className="captured-strip-pieces">
        {pieces.length === 0 ? (
          <span className="captured-empty">None</span>
        ) : (
          pieces.map((piece, index) => (
            <span key={`${piece}-${index}`}>{pieceGlyph(piece)}</span>
          ))
        )}
      </div>
    </div>
  )
}

function CapturedShelf({ capturedPieces }) {
  return (
    <div className="captured-shelf" aria-label="Captured pieces">
      <CapturedStrip label="White captured" pieces={capturedPieces.white} />
      <CapturedStrip label="Black captured" pieces={capturedPieces.black} />
    </div>
  )
}

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
    <aside className="panel move-panel">
      <h2>Moves</h2>
      <div className="move-history">
        {rows.length === 0 && <p className="muted">No moves yet</p>}
        {rows.map((row) => (
          <div className="move-row" key={row.number}>
            <span className="move-number">{row.number}.</span>
            <span className="move-white">{row.white}</span>
            <span className="move-black">{row.black || ''}</span>
          </div>
        ))}
      </div>
    </aside>
  )
}

export default function App() {
  const [board, setBoard] = useState(EMPTY_BOARD)
  const [currentTurn, setCurrentTurn] = useState('white')
  const [playerColor, setPlayerColor] = useState('white')
  const [engineColor, setEngineColor] = useState('black')
  const [gameOver, setGameOver] = useState(false)
  const [gameOverReason, setGameOverReason] = useState(null)
  const [winner, setWinner] = useState(null)
  const [moveLog, setMoveLog] = useState([])
  const [lastMove, setLastMove] = useState(null)
  const [capturedPieces, setCapturedPieces] = useState({ white: [], black: [] })
  const [evalScore, setEvalScore] = useState(0)
  const [timeLimitMs, setTimeLimitMs] = useState(1000)
  const [botLimitMode, setBotLimitMode] = useState('time')
  const [depthLimit, setDepthLimit] = useState(3)

  const [selectedSquare, setSelectedSquare] = useState(null)
  const [legalMoves, setLegalMoves] = useState([])
  const [thinking, setThinking] = useState(false)
  const [error, setError] = useState(null)
  const [ready, setReady] = useState(false)

  function applyState(data) {
    setBoard(data.board)
    setCurrentTurn(data.current_turn)
    setPlayerColor(data.player_color)
    setEngineColor(data.engine_color)
    setGameOver(data.game_over)
    setGameOverReason(data.game_over_reason)
    setWinner(data.winner)
    setMoveLog(data.move_log)
    setLastMove(data.last_move)
    setCapturedPieces(data.captured_pieces)
    setEvalScore(data.eval)
    setTimeLimitMs(data.bot_time_limit_ms)
    setBotLimitMode(data.bot_limit_mode || 'time')
    setDepthLimit(data.bot_depth_limit || 3)
  }

  useEffect(() => {
    getState()
      .then(applyState)
      .catch((e) => setError(e.message))
      .finally(() => setReady(true))
  }, [])

  function isOwnPiece(piece) {
    if (piece === 0) return false
    return currentTurn === playerColor && (piece > 0) === (playerColor === 'white')
  }

  async function selectSquare(row, col) {
    setSelectedSquare([row, col])
    try {
      const data = await getLegalMoves(row, col)
      setLegalMoves(data.moves)
    } catch (e) {
      setError(e.message)
    }
  }

  async function onSquareClick(row, col) {
    if (thinking || gameOver || currentTurn !== playerColor) return
    setError(null)

    const piece = board[row][col]

    if (selectedSquare) {
      const [sr, sc] = selectedSquare

      if (sr === row && sc === col) {
        setSelectedSquare(null)
        setLegalMoves([])
        return
      }

      const isLegalTarget = legalMoves.some(([r, c]) => r === row && c === col)
      if (isLegalTarget) {
        setSelectedSquare(null)
        setLegalMoves([])
        setThinking(true)
        try {
          const data = await makeMove(sr, sc, row, col)
          applyState(data)
        } catch (e) {
          setError(e.message)
        } finally {
          setThinking(false)
        }
        return
      }

      if (isOwnPiece(piece)) {
        selectSquare(row, col)
      } else {
        setSelectedSquare(null)
        setLegalMoves([])
      }
      return
    }

    if (isOwnPiece(piece)) {
      selectSquare(row, col)
    }
  }

  async function onNewGame(nextPlayerColor = playerColor) {
    setError(null)
    setSelectedSquare(null)
    setLegalMoves([])
    setThinking(true)
    try {
      const data = await newGame(nextPlayerColor)
      applyState(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setThinking(false)
    }
  }

  async function onPlayerColorChange(nextPlayerColor) {
    if (nextPlayerColor === playerColor || thinking) return
    await onNewGame(nextPlayerColor)
  }

  async function onUndo() {
    setError(null)
    setSelectedSquare(null)
    setLegalMoves([])
    setThinking(true)
    try {
      const data = await undoMove()
      applyState(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setThinking(false)
    }
  }

  async function onTimeLimitChange(newTimeLimitMs) {
    setTimeLimitMs(newTimeLimitMs)

    try {
      await setBotLimit({
        mode: botLimitMode,
        milliseconds: newTimeLimitMs,
        depth: depthLimit
      })
    } catch (e) {
      setError(e.message)
    }
  }

  async function onDepthLimitChange(newDepthLimit) {
    setDepthLimit(newDepthLimit)

    try {
      await setBotLimit({
        mode: botLimitMode,
        milliseconds: timeLimitMs,
        depth: newDepthLimit
      })
    } catch (e) {
      setError(e.message)
    }
  }

  async function onBotLimitModeChange(nextMode) {
    setBotLimitMode(nextMode)

    try {
      await setBotLimit({
        mode: nextMode,
        milliseconds: timeLimitMs,
        depth: depthLimit
      })
    } catch (e) {
      setError(e.message)
    }
  }

  return (
    <div className="app">
      <h1 className="title">Chess</h1>

      {error && <div className="error-banner">{error}</div>}

      {!ready ? (
        <p className="muted">Connecting to backend...</p>
      ) : (
        <div className="layout">
          <div className="play-area">
            <div className="board-column">
              <CapturedShelf capturedPieces={capturedPieces} />

              <div className="board-wrapper">
                <Board
                  board={board}
                  selectedSquare={selectedSquare}
                  legalMoves={legalMoves}
                  lastMove={lastMove}
                  onSquareClick={onSquareClick}
                  disabled={thinking || gameOver || currentTurn !== playerColor}
                  playerColor={playerColor}
                />

                {thinking && (
                  <div className="thinking-overlay">
                    <div className="thinking-card">Engine thinking...</div>
                  </div>
                )}
              </div>
            </div>

            <MoveHistory moveLog={moveLog} />
          </div>

          <Sidebar
            currentTurn={currentTurn}
            playerColor={playerColor}
            engineColor={engineColor}
            thinking={thinking}
            gameOver={gameOver}
            gameOverReason={gameOverReason}
            winner={winner}
            evalScore={evalScore}
            timeLimitMs={timeLimitMs}
            botLimitMode={botLimitMode}
            depthLimit={depthLimit}
            onTimeLimitChange={onTimeLimitChange}
            onDepthLimitChange={onDepthLimitChange}
            onBotLimitModeChange={onBotLimitModeChange}
            onNewGame={() => onNewGame(playerColor)}
            onUndo={onUndo}
            onPlayerColorChange={onPlayerColorChange}
          />
        </div>
      )}
    </div>
  )
}
