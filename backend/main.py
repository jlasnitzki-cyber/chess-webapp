"""
FastAPI backend for the chess web app.

Games are stored through a repository interface instead of process globals.
Redis is used when REDIS_URL is configured and reachable; otherwise the app
logs a warning and uses temporary in-memory storage for local development.
"""

from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import engine_w
import moves_w
import state_w
from game_store import GameNotFound, create_repository
from state_w import GameState


app = FastAPI()
repository = create_repository()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://chess-webapp-alpha.vercel.app",
        "https://lasnitzkichess.com",
        "https://www.lasnitzkichess.com",
        
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


class BotLimitRequest(BaseModel):
    mode: str
    milliseconds: Optional[int] = None
    depth: Optional[int] = None


class NewGameRequest(BaseModel):
    player_color: str = "white"


def set_repository(repo):
    global repository
    repository = repo


def validate_color(color: str):
    if color not in ("white", "black"):
        raise HTTPException(status_code=400, detail="Color must be white or black")


def validate_square(row: int, col: int):
    if not 0 <= row < 8 or not 0 <= col < 8:
        raise HTTPException(
            status_code=400,
            detail="Board coordinates must be between 0 and 7",
        )


def get_or_404(game_id: str) -> GameState:
    try:
        return repository.get_game(game_id)
    except GameNotFound:
        raise HTTPException(status_code=404, detail="Game not found")


def serialize_state(game: GameState, **extra):
    data = game.to_dict()
    data["current_turn_sign"] = game.current_turn
    data["current_turn"] = game.current_turn_color()
    data.update(extra)
    return data


def check_game_over_for_current_player(game: GameState):
    color = game.current_turn_color()
    result = moves_w.check_endgame(game, color)

    if result is None:
        game.game_over = False
        game.game_over_reason = None
        game.winner = None
        return None

    game.game_over = True
    game.game_over_reason = result
    game.winner = state_w.opposite_color(color) if result == "checkmate" else None
    return {"reason": result, "loser": color}


def is_player_turn(game: GameState):
    return game.current_turn_color() == game.player_color


def is_engine_turn(game: GameState):
    return game.current_turn_color() == game.engine_color()


def apply_bot_limit(game: GameState, req: BotLimitRequest):
    if req.mode not in ("time", "depth"):
        raise HTTPException(status_code=400, detail="Mode must be time or depth")

    if req.milliseconds is not None:
        if req.milliseconds < 100 or req.milliseconds > 10000:
            raise HTTPException(
                status_code=400,
                detail="Time limit must be between 100ms and 10000ms",
            )
        game.bot_time_limit_ms = req.milliseconds

    if req.depth is not None:
        if req.depth < 1 or req.depth > 6:
            raise HTTPException(
                status_code=400,
                detail="Depth limit must be between 1 and 6",
            )
        game.bot_depth_limit = req.depth

    game.bot_limit_mode = req.mode


@app.post("/games")
def create_game(req: Optional[NewGameRequest] = None):
    player_color = req.player_color if req else "white"
    validate_color(player_color)

    game = GameState(player_color=player_color)
    repository.create_game(game)
    return serialize_state(game)


@app.get("/games/{game_id}")
def get_game(game_id: str):
    return serialize_state(get_or_404(game_id))


@app.post("/games/{game_id}/reset")
def reset_game(game_id: str, req: Optional[NewGameRequest] = None):
    with repository.lock_game(game_id):
        game = get_or_404(game_id)
        player_color = req.player_color if req else game.player_color
        validate_color(player_color)
        game.reset(player_color)
        repository.save_game(game)
        return serialize_state(game)


@app.delete("/games/{game_id}")
def delete_game(game_id: str):
    repository.delete_game(game_id)
    return {"deleted": True, "game_id": game_id}


@app.get("/games/{game_id}/legal-moves")
def legal_moves(game_id: str, row: int, col: int):
    validate_square(row, col)
    game = get_or_404(game_id)
    piece = game.board[row][col]

    if piece == 0:
        return {"game_id": game_id, "moves": []}

    piece_color = "white" if piece > 0 else "black"
    if not is_player_turn(game) or piece_color != game.player_color:
        return {"game_id": game_id, "moves": []}

    return {"game_id": game_id, "moves": moves_w.get_legal_moves(game, row, col)}


@app.post("/games/{game_id}/move")
def make_move(game_id: str, req: MoveRequest):
    validate_square(req.start_row, req.start_col)
    validate_square(req.end_row, req.end_col)

    try:
        with repository.lock_game(game_id):
            game = get_or_404(game_id)
            if game.game_over:
                raise HTTPException(status_code=400, detail="Game is already over")
            if game.engine_thinking:
                raise HTTPException(status_code=409, detail="Engine is already thinking")
            if not is_player_turn(game):
                raise HTTPException(status_code=400, detail="It is not the player's turn")

            piece = game.board[req.start_row][req.start_col]
            if piece == 0:
                raise HTTPException(status_code=400, detail="No piece on that square")

            piece_color = "white" if piece > 0 else "black"
            if piece_color != game.player_color:
                raise HTTPException(
                    status_code=400, detail="You cannot move the engine's pieces"
                )

            if not state_w.make_move(
                game, req.start_row, req.start_col, req.end_row, req.end_col
            ):
                raise HTTPException(status_code=400, detail="Illegal move")

            check_game_over_for_current_player(game)
            repository.save_game(game)
            return serialize_state(game)
    except TimeoutError:
        raise HTTPException(status_code=409, detail="Game is busy")


@app.post("/games/{game_id}/engine-move")
def make_engine_move(game_id: str):
    try:
        with repository.lock_game(game_id):
            game = get_or_404(game_id)
            if game.game_over:
                raise HTTPException(status_code=400, detail="Game is already over")
            if game.engine_thinking:
                raise HTTPException(status_code=409, detail="Engine is already thinking")
            if not is_engine_turn(game):
                raise HTTPException(status_code=400, detail="It is not the engine's turn")

            game.engine_thinking = True
            start_version = game.position_version
            search_color = game.current_turn_color()
            search_game = GameState.from_dict(game.to_dict())
            repository.save_game(game)
    except TimeoutError:
        raise HTTPException(status_code=409, detail="Game is busy")

    best_move, search_context = engine_w.find_best_engine_move(search_game, search_color)

    try:
        with repository.lock_game(game_id):
            game = get_or_404(game_id)

            if game.position_version != start_version or game.current_turn_color() != search_color:
                game.engine_thinking = False
                repository.save_game(game)
                return serialize_state(
                    game,
                    engine_result_discarded=True,
                    search_nodes=search_context.nodes,
                )

            if best_move is not None:
                state_w.make_move(game, *best_move)

            game.engine_thinking = False
            check_game_over_for_current_player(game)
            repository.save_game(game)
            return serialize_state(
                game,
                engine_result_discarded=False,
                search_nodes=search_context.nodes,
            )
    except TimeoutError:
        raise HTTPException(status_code=409, detail="Game is busy")


@app.post("/games/{game_id}/bot-limit")
def set_bot_limit(game_id: str, req: BotLimitRequest):
    try:
        with repository.lock_game(game_id):
            game = get_or_404(game_id)
            apply_bot_limit(game, req)
            game.position_version += 1
            repository.save_game(game)
            return serialize_state(game)
    except TimeoutError:
        raise HTTPException(status_code=409, detail="Game is busy")


@app.post("/games/{game_id}/time-limit")
def set_time_limit(game_id: str, req: TimeLimitRequest):
    return set_bot_limit(
        game_id,
        BotLimitRequest(mode="time", milliseconds=req.milliseconds),
    )


@app.post("/games/{game_id}/undo")
def undo(game_id: str):
    try:
        with repository.lock_game(game_id):
            game = get_or_404(game_id)
            if game.engine_thinking:
                raise HTTPException(status_code=409, detail="Engine is already thinking")

            player_sign = state_w.color_to_sign(game.player_color)
            player_move_index = None

            for index in range(len(game.piece_history) - 1, -1, -1):
                if game.piece_history[index] * player_sign > 0:
                    player_move_index = index
                    break

            if player_move_index is None:
                return serialize_state(game)

            while len(game.move_history) - 1 > player_move_index:
                state_w.undo_move(game)

            state_w.undo_move(game)
            game.game_over = False
            game.game_over_reason = None
            game.winner = None
            repository.save_game(game)
            return serialize_state(game)
    except TimeoutError:
        raise HTTPException(status_code=409, detail="Game is busy")


# Compatibility aliases for the existing React route names during migration.
@app.post("/api/new-game")
def api_new_game(req: Optional[NewGameRequest] = None):
    return create_game(req)


@app.get("/api/state")
def api_state(game_id: str):
    return get_game(game_id)


@app.get("/api/legal-moves")
def api_legal_moves(game_id: str, row: int, col: int):
    return legal_moves(game_id, row, col)


@app.post("/api/move")
def api_move(game_id: str, req: MoveRequest):
    return make_move(game_id, req)


@app.post("/api/engine-move")
def api_engine_move(game_id: str):
    return make_engine_move(game_id)


@app.post("/api/undo")
def api_undo(game_id: str):
    return undo(game_id)


@app.post("/api/bot-limit")
def api_bot_limit(game_id: str, req: BotLimitRequest):
    return set_bot_limit(game_id, req)


@app.post("/api/time-limit")
def api_time_limit(game_id: str, req: TimeLimitRequest):
    return set_time_limit(game_id, req)
