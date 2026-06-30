// Piece encoding matches config_w.py: 1 king, 2 queen, 3 bishop,
// 4 knight, 5 rook, 6 pawn. Positive = white, negative = black.

const WHITE_GLYPHS = {
  1: '\u2654',
  2: '\u2655',
  3: '\u2657',
  4: '\u2658',
  5: '\u2656',
  6: '\u2659'
}

const BLACK_GLYPHS = {
  1: '\u265a',
  2: '\u265b',
  3: '\u265d',
  4: '\u265e',
  5: '\u265c',
  6: '\u265f'
}

export function pieceGlyph(piece) {
  if (piece === 0) return null
  const type = Math.abs(piece)
  return piece > 0 ? WHITE_GLYPHS[type] : BLACK_GLYPHS[type]
}

export function pieceColor(piece) {
  if (piece === 0) return null
  return piece > 0 ? 'white' : 'black'
}
