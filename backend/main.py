"""
FastAPI backend for the chess web app.

This file is the ONLY new file in the backend. It imports your existing
engine modules (state_w, moves_w, engine_w, notation_w) unchanged and
exposes them over HTTP.

Note on architecture: state_w.py stores the game as module-level globals
(state_w.board, state_w.current_turn, etc). That means this server has a
single shared game for the whole process - perfect for one person playing
in one browser, but a second simultaneous browser tab would see/affect the
same game. If you ever want multiple independent games running at once,
this is the file that would need to change (wrap the globals in a class,
keep a dict of instances keyed by game id). For now, single-game is what we
want.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import config_w
import engine_w
import moves_w
import notation_w
import state_w
import time
from typing import Optional

app = FastAPI()

# Allow the Vite dev server to call this API from a different port.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://chess-webapp-alpha.vercel.app",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


class MoveRequest(BaseModel):
    start_row: int
    start_col: int
    end_row: int
    end_col: int


class TimeLimitRequest(BaseModel):
    milliseconds: int


class NewGameRequest(BaseModel):
    player_color: str = "white"


def validate_color(color: str):
    if color not in ("white", "black"):
        raise HTTPException(status_code=400, detail="Color must be white or black")


def is_player_turn():
    return state_w.current_turn_color() == state_w.player_color


def is_engine_turn():
    return state_w.current_turn_color() == state_w.engine_color()


def make_engine_move_if_needed():
    if state_w.game_over or not is_engine_turn():
        return None

    engine_w.get_best_move(state_w.engine_color())
    return check_game_over_for_current_player()


def check_game_over_for_current_player():
    """Looks at whoever is about to move and records checkmate/stalemate."""
    color = state_w.current_turn_color()
    result = moves_w.check_endgame(state_w.board, color)

    if result is None:
        state_w.game_over = False
        return None

    state_w.game_over = True
    return {"reason": result, "loser": color}


def serialize_state(game_over_info=None):
    if game_over_info is None and state_w.game_over:
        # Re-derive it (covers the case right after server start / reload)
        game_over_info = check_game_over_for_current_player()

    winner = None
    if game_over_info and game_over_info["reason"] == "checkmate":
        winner = "black" if game_over_info["loser"] == "white" else "white"

    return {
        "board": state_w.board,
        "current_turn": state_w.current_turn_color(),
        "player_color": state_w.player_color,
        "engine_color": state_w.engine_color(),
        "game_over": state_w.game_over,
        "game_over_reason": game_over_info["reason"] if game_over_info else None,
        "winner": winner,
        "move_log": state_w.move_notation_history,
        "last_move": state_w.last_move,
        "captured_pieces": state_w.captured_pieces,
        "eval": state_w.evaluation(state_w.captured_pieces),
        "bot_time_limit_ms": state_w.bot_time_limit_ms,
    }


@app.post("/api/new-game")
def new_game(req: Optional[NewGameRequest] = None):
    player_color = req.player_color if req else "white"
    validate_color(player_color)

    state_w.reset_game(player_color)
    game_over_info = make_engine_move_if_needed()
    return serialize_state(game_over_info)


@app.get("/api/state")
def get_state():
    return serialize_state()

def validate_square(row: int, col: int):
    if not 0 <= row < 8 or not 0 <= col < 8:
        raise HTTPException(
            status_code=400,
            detail="Board coordinates must be between 0 and 7",
        )

@app.get("/api/legal-moves")
def legal_moves(row: int, col: int):
    validate_square(row, col)
    piece = state_w.board[row][col]

    if piece == 0:
        return {"moves": []}

    piece_color = "white" if piece > 0 else "black"

    if not is_player_turn() or piece_color != state_w.player_color:
        return {"moves": []}

    moves = moves_w.get_legal_moves(state_w.board, row, col)
    return {"moves": moves}

@app.post("/api/move")
def make_move(req: MoveRequest):
    validate_square(req.start_row, req.start_col)
    validate_square(req.end_row, req.end_col)
    if state_w.game_over:
        raise HTTPException(status_code=400, detail="Game is already over")
    if not is_player_turn():
        raise HTTPException(status_code=400, detail="It is not the player's turn")

    piece = state_w.board[req.start_row][req.start_col]
    if piece == 0:
        raise HTTPException(status_code=400, detail="No piece on that square")

    piece_color = "white" if piece > 0 else "black"
    if piece_color != state_w.player_color:
        raise HTTPException(status_code=400, detail="You cannot move the engine's pieces")

    if not moves_w.is_legal_move(
        state_w.board, req.start_row, req.start_col, req.end_row, req.end_col
    ):
        raise HTTPException(status_code=400, detail="Illegal move")

    # --- Human move ---
    state_w.make_move(req.start_row, req.start_col, req.end_row, req.end_col)

    game_over_info = check_game_over_for_current_player()
    if game_over_info:
        return serialize_state(game_over_info)

    # --- Engine move ---
    start_time = time.perf_counter()

    engine_w.get_best_move(state_w.engine_color())

    elapsed = time.perf_counter() - start_time
    game_over_info = check_game_over_for_current_player()
    return serialize_state(game_over_info)


@app.post("/api/undo")
def undo():
    player_sign = state_w.color_to_sign(state_w.player_color)
    player_move_index = None

    for index in range(len(state_w.piece_history) - 1, -1, -1):
        if state_w.piece_history[index] * player_sign > 0:
            player_move_index = index
            break

    if player_move_index is None:
        return serialize_state()

    while len(state_w.move_history) - 1 > player_move_index:
        state_w.undo_move()

    state_w.undo_move()

    state_w.game_over = False
    return serialize_state()


@app.post("/api/time-limit")
def set_time_limit(req: TimeLimitRequest):
    if req.milliseconds < 100 or req.milliseconds > 10000:
        raise HTTPException(
            status_code=400,
            detail="Time limit must be between 100ms and 10000ms",
        )
    state_w.bot_time_limit_ms = req.milliseconds
    return {"bot_time_limit_ms": state_w.bot_time_limit_ms}
