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

app = FastAPI()

# Allow the Vite dev server to call this API from a different port.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class MoveRequest(BaseModel):
    start_row: int
    start_col: int
    end_row: int
    end_col: int


class DepthRequest(BaseModel):
    depth: int


def check_game_over_for_current_player():
    """Looks at whoever is about to move and records checkmate/stalemate."""
    color = "white" if state_w.current_turn == 1 else "black"
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
        "current_turn": "white" if state_w.current_turn == 1 else "black",
        "game_over": state_w.game_over,
        "game_over_reason": game_over_info["reason"] if game_over_info else None,
        "winner": winner,
        "move_log": state_w.move_notation_history,
        "last_move": state_w.last_move,
        "captured_pieces": state_w.captured_pieces,
        "eval": state_w.evaluation(state_w.captured_pieces),
        "bot_search_depth": state_w.bot_search_depth,
    }


@app.post("/api/new-game")
def new_game():
    state_w.reset_game()
    return serialize_state()


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

    piece_is_white = piece > 0
    player_to_move_is_white = state_w.current_turn == 1

    if piece_is_white != player_to_move_is_white:
        return {"moves": []}

    moves = moves_w.get_legal_moves(state_w.board, row, col)
    return {"moves": moves}

@app.post("/api/move")
def make_move(req: MoveRequest):
    validate_square(req.start_row, req.start_col)
    validate_square(req.end_row, req.end_col)
    if state_w.game_over:
        raise HTTPException(status_code=400, detail="Game is already over")

    piece = state_w.board[req.start_row][req.start_col]
    if piece == 0:
        raise HTTPException(status_code=400, detail="No piece on that square")

    piece_is_white = piece > 0
    player_to_move_is_white = state_w.current_turn == 1
    if piece_is_white != player_to_move_is_white:
        raise HTTPException(status_code=400, detail="It's not that color's turn")

    if not moves_w.is_legal_move(
        state_w.board, req.start_row, req.start_col, req.end_row, req.end_col
    ):
        raise HTTPException(status_code=400, detail="Illegal move")

    # --- Human move ---
    state_w.make_move(req.start_row, req.start_col, req.end_row, req.end_col)

    game_over_info = check_game_over_for_current_player()
    if game_over_info:
        return serialize_state(game_over_info)

    # --- Bot move ---
    engine_w.get_best_move()

    game_over_info = check_game_over_for_current_player()
    return serialize_state(game_over_info)


@app.post("/api/undo")
def undo():
    # One full round = human move + bot move. Undo both so it's the
    # human's turn again at the position before their last move.
    if state_w.current_turn == 1:
        # It's currently white's turn, meaning black (the bot) just moved.
        state_w.undo_move()  # undoes bot's move
    if state_w.move_history:
        state_w.undo_move()  # undoes human's move

    state_w.game_over = False
    return serialize_state()


@app.post("/api/depth")
def set_depth(req: DepthRequest):
    if req.depth < 1 or req.depth > 5:
        raise HTTPException(status_code=400, detail="Depth must be between 1 and 5")
    state_w.bot_search_depth = req.depth
    return {"bot_search_depth": state_w.bot_search_depth}
