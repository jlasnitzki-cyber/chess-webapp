import { pieceGlyph, pieceColor } from './pieces.js'

function squareKey(row, col) {
  return `${row}-${col}`
}

function displayToBoard(row, col, playerColor) {
  if (playerColor === 'black') {
    return [7 - row, 7 - col]
  }
  return [row, col]
}

export default function Board({
  board,
  selectedSquare,
  legalMoves,
  lastMove,
  onSquareClick,
  disabled,
  playerColor
}) {
  const legalSet = new Set((legalMoves || []).map(([r, c]) => squareKey(r, c)))
  const lastMoveSet = new Set(
    lastMove ? lastMove.map(([r, c]) => squareKey(r, c)) : []
  )

  return (
    <div className={`board ${disabled ? 'board-disabled' : ''}`}>
      {Array.from({ length: 8 }, (_, displayRow) =>
        Array.from({ length: 8 }, (_, displayCol) => {
          const [row, col] = displayToBoard(displayRow, displayCol, playerColor)
          const piece = board[row][col]
          const isLight = (row + col) % 2 === 0
          const isSelected =
            selectedSquare && selectedSquare[0] === row && selectedSquare[1] === col
          const isLegalTarget = legalSet.has(squareKey(row, col))
          const isLastMove = lastMoveSet.has(squareKey(row, col))
          const glyph = pieceGlyph(piece)
          const color = pieceColor(piece)

          const classes = [
            'square',
            isLight ? 'square-light' : 'square-dark',
            isSelected ? 'square-selected' : '',
            isLastMove ? 'square-last-move' : ''
          ]
            .filter(Boolean)
            .join(' ')

          return (
            <button
              key={squareKey(row, col)}
              className={classes}
              onClick={() => onSquareClick(row, col)}
              disabled={disabled}
              aria-label={`Square ${row},${col}${glyph ? `, ${color} piece` : ', empty'}`}
            >
              {isLegalTarget && !glyph && <span className="move-dot" />}
              {isLegalTarget && glyph && <span className="capture-ring" />}
              {glyph && <span className={`piece piece-${color}`}>{glyph}</span>}
            </button>
          )
        })
      )}
    </div>
  )
}
