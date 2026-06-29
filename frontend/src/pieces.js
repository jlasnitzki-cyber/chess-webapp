// Piece encoding matches config_w.py: 1 king, 2 queen, 3 bishop,
// 4 knight, 5 rook, 6 pawn. Positive = white, negative = black.

const WHITE_GLYPHS = { 1: '♔', 2: '♕', 3: '♗', 4: '♘', 5: '♖', 6: '♙' }
const BLACK_GLYPHS = { 1: '♚', 2: '♛', 3: '♝', 4: '♞', 5: '♜', 6: '♟' }

export function pieceGlyph(piece) {
  if (piece === 0) return null
  const type = Math.abs(piece)
  return piece > 0 ? WHITE_GLYPHS[type] : BLACK_GLYPHS[type]
}

export function pieceColor(piece) {
  if (piece === 0) return null
  return piece > 0 ? 'white' : 'black'
}
