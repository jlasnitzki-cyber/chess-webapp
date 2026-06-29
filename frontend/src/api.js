const BASE_URL =
  import.meta.env.VITE_API_URL || (import.meta.env.DEV ? 'http://127.0.0.1:8000' : '')

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers
    },
    ...options
  })

  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `Request to ${path} failed`)
  }

  return res.json()
}
export function newGame(playerColor = 'white') {
  return request('/api/new-game', {
    method: 'POST',
    body: JSON.stringify({ player_color: playerColor })
  })
}

export function getState() {
  return request('/api/state')
}

export function getLegalMoves(row, col) {
  return request(`/api/legal-moves?row=${row}&col=${col}`)
}

export function makeMove(startRow, startCol, endRow, endCol) {
  return request('/api/move', {
    method: 'POST',
    body: JSON.stringify({
      start_row: startRow,
      start_col: startCol,
      end_row: endRow,
      end_col: endCol
    })
  })
}

export function undoMove() {
  return request('/api/undo', { method: 'POST' })
}

export function setTimeLimit(milliseconds) {
  return request('/api/time-limit', {
    method: 'POST',
    body: JSON.stringify({ milliseconds })
  })
}
