import { useEffect, useState } from 'react'
import Board from './Board.jsx'
import Sidebar from './Sidebar.jsx'
import {
  getState,
  newGame,
  getLegalMoves,
  makeMove,
  undoMove,
  setDepth as apiSetDepth
} from './api.js'

const EMPTY_BOARD = Array.from({ length: 8 }, () => Array(8).fill(0))

export default function App() {
  const [board, setBoard] = useState(EMPTY_BOARD)
  const [currentTurn, setCurrentTurn] = useState('white')
  const [gameOver, setGameOver] = useState(false)
  const [gameOverReason, setGameOverReason] = useState(null)
  const [winner, setWinner] = useState(null)
  const [moveLog, setMoveLog] = useState([])
  const [lastMove, setLastMove] = useState(null)
  const [capturedPieces, setCapturedPieces] = useState({ white: [], black: [] })
  const [evalScore, setEvalScore] = useState(0)
  const [depth, setDepthState] = useState(3)

  const [selectedSquare, setSelectedSquare] = useState(null)
  const [legalMoves, setLegalMoves] = useState([])
  const [thinking, setThinking] = useState(false)
  const [error, setError] = useState(null)
  const [ready, setReady] = useState(false)

  function applyState(data) {
    setBoard(data.board)
    setCurrentTurn(data.current_turn)
    setGameOver(data.game_over)
    setGameOverReason(data.game_over_reason)
    setWinner(data.winner)
    setMoveLog(data.move_log)
    setLastMove(data.last_move)
    setCapturedPieces(data.captured_pieces)
    setEvalScore(data.eval)
    setDepthState(data.bot_search_depth)
  }

  useEffect(() => {
    getState()
      .then(applyState)
      .catch((e) => setError(e.message))
      .finally(() => setReady(true))
  }, [])

  function isOwnPiece(piece) {
    if (piece === 0) return false
    return (piece > 0) === (currentTurn === 'white')
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
    if (thinking || gameOver) return
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

  async function onNewGame() {
    setError(null)
    setSelectedSquare(null)
    setLegalMoves([])
    try {
      const data = await newGame()
      applyState(data)
    } catch (e) {
      setError(e.message)
    }
  }

  async function onUndo() {
    setError(null)
    setSelectedSquare(null)
    setLegalMoves([])
    try {
      const data = await undoMove()
      applyState(data)
    } catch (e) {
      setError(e.message)
    }
  }

  async function onDepthChange(newDepth) {
  setDepthState(newDepth)

  try {
    await apiSetDepth(newDepth)
  } catch (e) {
    setError(e.message)
  }
}

return (
  <div className="app">
    <h1 className="title">Chess</h1>

    {error && <div className="error-banner">{error}</div>}

    {!ready ? (
      <p className="muted">Connecting to backend…</p>
    ) : (
      <div className="layout">
        <div className="board-wrapper">
          <Board
            board={board}
            selectedSquare={selectedSquare}
            legalMoves={legalMoves}
            lastMove={lastMove}
            onSquareClick={onSquareClick}
            disabled={thinking || gameOver}
          />

          {thinking && (
            <div className="thinking-overlay">
              <div className="thinking-card">Engine thinking…</div>
            </div>
          )}
        </div>

        <Sidebar
          currentTurn={currentTurn}
          thinking={thinking}
          gameOver={gameOver}
          gameOverReason={gameOverReason}
          winner={winner}
          evalScore={evalScore}
          depth={depth}
          onDepthChange={onDepthChange}
          onNewGame={onNewGame}
          onUndo={onUndo}
          moveLog={moveLog}
          capturedPieces={capturedPieces}
        />
      </div>
    )}
  </div>
)
}
