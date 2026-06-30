const BASE_URL =
  import.meta.env.VITE_API_URL || (import.meta.env.DEV ? 'http://127.0.0.1:8000' : '')

const GAME_ID_KEY = 'chess_webapp_game_id'

function getStoredGameId() {
  return window.localStorage.getItem(GAME_ID_KEY)
}

function storeGameId(gameId) {
  if (gameId) {
    window.localStorage.setItem(GAME_ID_KEY, gameId)
  }
}

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

  const data = await res.json()
  if (data.game_id) storeGameId(data.game_id)
  return data
}

async function requestCurrentGame(path, options = {}) {
  const gameId = getStoredGameId()
  if (!gameId) {
    return newGame('white')
  }
  return request(`/games/${gameId}${path}`, options)
}

export async function newGame(playerColor = 'white') {
  const data = await request('/games', {
    method: 'POST',
    body: JSON.stringify({ player_color: playerColor })
  })

  if (!data.game_over && data.current_turn === data.engine_color) {
    return request(`/games/${data.game_id}/engine-move`, { method: 'POST' })
  }

  return data
}

export async function getState() {
  const gameId = getStoredGameId()
  if (!gameId) {
    return newGame('white')
  }

  try {
    return await request(`/games/${gameId}`)
  } catch (error) {
    window.localStorage.removeItem(GAME_ID_KEY)
    return newGame('white')
  }
}

export function getLegalMoves(row, col) {
  return requestCurrentGame(`/legal-moves?row=${row}&col=${col}`)
}

export async function makeMove(startRow, startCol, endRow, endCol) {
  const data = await requestCurrentGame('/move', {
    method: 'POST',
    body: JSON.stringify({
      start_row: startRow,
      start_col: startCol,
      end_row: endRow,
      end_col: endCol
    })
  })

  if (!data.game_over && data.current_turn === data.engine_color) {
    return requestCurrentGame('/engine-move', { method: 'POST' })
  }

  return data
}

export function undoMove() {
  return requestCurrentGame('/undo', { method: 'POST' })
}

export function setTimeLimit(milliseconds) {
  return requestCurrentGame('/time-limit', {
    method: 'POST',
    body: JSON.stringify({ milliseconds })
  })
}

export function setBotLimit({ mode, milliseconds, depth }) {
  return requestCurrentGame('/bot-limit', {
    method: 'POST',
    body: JSON.stringify({ mode, milliseconds, depth })
  })
}
