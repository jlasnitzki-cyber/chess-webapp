import copy
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

import config_w


def color_to_sign(color: str) -> int:
    return 1 if color == "white" else -1


def sign_to_color(sign: int) -> str:
    return "white" if sign == 1 else "black"


def opposite_color(color: str) -> str:
    return "black" if color == "white" else "white"


def _tuple_or_none(value):
    return tuple(value) if value is not None else None


def _last_move_to_tuple(value):
    if value is None:
        return None
    return (tuple(value[0]), tuple(value[1]))


def _move_history_to_tuples(values):
    return [(tuple(start), tuple(end)) for start, end in values]


def _state_history_to_dicts(values):
    states = []
    for state in values:
        state_copy = dict(state)
        state_copy["has_moved"] = sorted(state_copy.get("has_moved", []))
        if state_copy.get("en_passant_target") is not None:
            state_copy["en_passant_target"] = list(state_copy["en_passant_target"])
        if state_copy.get("last_move") is not None:
            state_copy["last_move"] = [
                list(state_copy["last_move"][0]),
                list(state_copy["last_move"][1]),
            ]
        states.append(state_copy)
    return states


def _state_history_from_dicts(values):
    states = []
    for state in values:
        state_copy = dict(state)
        state_copy["has_moved"] = set(state_copy.get("has_moved", []))
        state_copy["en_passant_target"] = _tuple_or_none(
            state_copy.get("en_passant_target")
        )
        state_copy["last_move"] = _last_move_to_tuple(state_copy.get("last_move"))
        states.append(state_copy)
    return states


@dataclass
class GameState:
    player_color: str = "white"
    game_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    board: list[list[int]] = field(
        default_factory=lambda: copy.deepcopy(config_w.board_start)
    )
    current_turn: int = 1
    move_history: list[tuple[tuple[int, int], tuple[int, int]]] = field(
        default_factory=list
    )
    move_notation_history: list[str] = field(default_factory=list)
    board_history: list[list[list[int]]] = field(default_factory=list)
    state_history: list[dict[str, Any]] = field(default_factory=list)
    piece_history: list[int] = field(default_factory=list)
    last_move: Optional[tuple[tuple[int, int], tuple[int, int]]] = None
    has_moved: set[str] = field(default_factory=set)
    en_passant_target: Optional[tuple[int, int]] = None
    game_over: bool = False
    game_over_reason: Optional[str] = None
    winner: Optional[str] = None
    player_color_override: Optional[str] = None
    bot_color: Optional[str] = None
    bot_time_limit_ms: int = 1000
    bot_limit_mode: str = "time"
    bot_depth_limit: int = 3
    position_version: int = 0
    engine_thinking: bool = False
    captured_pieces: dict[str, list[int]] = field(
        default_factory=lambda: {"white": [], "black": []}
    )
    move_count: int = 0

    def __post_init__(self):
        if self.bot_color is None:
            self.bot_color = opposite_color(self.player_color)

    def current_turn_color(self) -> str:
        return sign_to_color(self.current_turn)

    def engine_color(self) -> str:
        return self.bot_color or opposite_color(self.player_color)

    def snapshot_state(self) -> dict[str, Any]:
        return {
            "current_turn": self.current_turn,
            "en_passant_target": self.en_passant_target,
            "captured_pieces": copy.deepcopy(self.captured_pieces),
            "has_moved": set(self.has_moved),
            "last_move": self.last_move,
            "move_count": self.move_count,
            "game_over": self.game_over,
            "game_over_reason": self.game_over_reason,
            "winner": self.winner,
            "position_version": self.position_version,
        }

    def reset(self, player_color: Optional[str] = None):
        if player_color is not None:
            self.player_color = player_color
            self.bot_color = opposite_color(player_color)

        self.board = copy.deepcopy(config_w.board_start)
        self.current_turn = 1
        self.move_history = []
        self.move_notation_history = []
        self.board_history = []
        self.state_history = []
        self.piece_history = []
        self.last_move = None
        self.has_moved = set()
        self.en_passant_target = None
        self.game_over = False
        self.game_over_reason = None
        self.winner = None
        self.position_version += 1
        self.engine_thinking = False
        self.captured_pieces = {"white": [], "black": []}
        self.move_count = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "game_id": self.game_id,
            "board": self.board,
            "current_turn": self.current_turn,
            "current_turn_color": self.current_turn_color(),
            "move_history": [
                [list(start), list(end)] for start, end in self.move_history
            ],
            "move_notation_history": self.move_notation_history,
            "move_log": self.move_notation_history,
            "board_history": self.board_history,
            "state_history": _state_history_to_dicts(self.state_history),
            "piece_history": self.piece_history,
            "last_move": (
                [list(self.last_move[0]), list(self.last_move[1])]
                if self.last_move
                else None
            ),
            "has_moved": sorted(self.has_moved),
            "castling_rights": sorted(self.has_moved),
            "en_passant_target": (
                list(self.en_passant_target) if self.en_passant_target else None
            ),
            "game_over": self.game_over,
            "game_over_reason": self.game_over_reason,
            "winner": self.winner,
            "player_color": self.player_color,
            "bot_color": self.engine_color(),
            "engine_color": self.engine_color(),
            "bot_time_limit_ms": self.bot_time_limit_ms,
            "bot_limit_mode": self.bot_limit_mode,
            "bot_depth_limit": self.bot_depth_limit,
            "position_version": self.position_version,
            "engine_thinking": self.engine_thinking,
            "captured_pieces": self.captured_pieces,
            "eval": evaluation(self.captured_pieces),
            "move_count": self.move_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GameState":
        game = cls(
            player_color=data.get("player_color", "white"),
            game_id=data.get("game_id") or str(uuid.uuid4()),
        )
        game.board = copy.deepcopy(data.get("board", config_w.board_start))
        current_turn = data.get("current_turn", 1)
        if isinstance(current_turn, str):
            current_turn = color_to_sign(current_turn)
        game.current_turn = current_turn
        game.move_history = _move_history_to_tuples(data.get("move_history", []))
        game.move_notation_history = list(
            data.get("move_notation_history", data.get("move_log", []))
        )
        game.board_history = copy.deepcopy(data.get("board_history", []))
        game.state_history = _state_history_from_dicts(data.get("state_history", []))
        game.piece_history = list(data.get("piece_history", []))
        game.last_move = _last_move_to_tuple(data.get("last_move"))
        game.has_moved = set(data.get("has_moved", data.get("castling_rights", [])))
        game.en_passant_target = _tuple_or_none(data.get("en_passant_target"))
        game.game_over = data.get("game_over", False)
        game.game_over_reason = data.get("game_over_reason")
        game.winner = data.get("winner")
        game.bot_color = data.get("bot_color", data.get("engine_color")) or opposite_color(
            game.player_color
        )
        game.bot_time_limit_ms = data.get("bot_time_limit_ms", 1000)
        game.bot_limit_mode = data.get("bot_limit_mode", "time")
        game.bot_depth_limit = data.get("bot_depth_limit", 3)
        game.position_version = data.get("position_version", 0)
        game.engine_thinking = data.get("engine_thinking", False)
        game.captured_pieces = copy.deepcopy(
            data.get("captured_pieces", {"white": [], "black": []})
        )
        game.move_count = data.get("move_count", len(game.move_history))
        return game


def evaluation(captured_pieces: dict[str, list[int]]) -> int:
    white_values = [
        config_w.piece_values[abs(piece)] for piece in captured_pieces["white"]
    ]
    black_values = [
        config_w.piece_values[abs(piece)] * -1
        for piece in captured_pieces["black"]
    ]
    return sum(white_values) + sum(black_values)


def captured_rook_right(captured_piece: int, row: int, col: int) -> Optional[str]:
    if abs(captured_piece) != 5:
        return None
    if captured_piece > 0 and row == 7 and col in (0, 7):
        return f"white_rook_{col}"
    if captured_piece < 0 and row == 0 and col in (0, 7):
        return f"black_rook_{col}"
    return None


def update_castling_rights(
    game: GameState,
    piece: int,
    start_row: int,
    start_col: int,
    end_col: int,
    captured_piece: int,
    capture_row: int,
    capture_col: int,
):
    color = "white" if piece > 0 else "black"

    if abs(piece) == 1:
        game.has_moved.add(f"{color}_king")
        if abs(end_col - start_col) == 2:
            game.has_moved.add(f"{color}_rook_{7 if end_col == 6 else 0}")
    elif abs(piece) == 5:
        home_row = 7 if color == "white" else 0
        if start_row == home_row and start_col in (0, 7):
            game.has_moved.add(f"{color}_rook_{start_col}")

    captured_right = captured_rook_right(captured_piece, capture_row, capture_col)
    if captured_right is not None:
        game.has_moved.add(captured_right)


def make_move(game: GameState, start_row: int, start_col: int, end_row: int, end_col: int):
    import moves_w
    import notation_w

    if not moves_w.is_legal_move(game, start_row, start_col, end_row, end_col):
        return False

    board_before_move = copy.deepcopy(game.board)
    game.board_history.append(board_before_move)
    game.state_history.append(game.snapshot_state())
    game.move_history.append(((start_row, start_col), (end_row, end_col)))
    game.piece_history.append(game.board[start_row][start_col])

    piece = game.board[start_row][start_col]
    color = "white" if piece > 0 else "black"
    capture_row, capture_col = end_row, end_col
    if (
        abs(piece) == 6
        and game.board[end_row][end_col] == 0
        and abs(end_col - start_col) == 1
        and (end_row, end_col) == game.en_passant_target
    ):
        capture_row, capture_col = start_row, end_col

    captured_piece, game.en_passant_target = moves_w.apply_special_moves(
        game.board,
        start_row,
        start_col,
        end_row,
        end_col,
        game.en_passant_target,
    )

    move_notation = notation_w.move_to_notation(
        game,
        board_before_move,
        piece,
        start_row,
        start_col,
        end_row,
        end_col,
        captured_piece,
    )
    if moves_w.is_in_check(game, opposite_color(color)):
        move_notation += "+"
    game.move_notation_history.append(move_notation)

    if captured_piece != 0:
        game.captured_pieces[color].append(captured_piece)

    update_castling_rights(
        game,
        piece,
        start_row,
        start_col,
        end_col,
        captured_piece,
        capture_row,
        capture_col,
    )

    game.last_move = ((start_row, start_col), (end_row, end_col))
    game.move_count += 1
    game.current_turn *= -1
    game.position_version += 1
    game.game_over = False
    game.game_over_reason = None
    game.winner = None
    return True


def undo_move(game: GameState):
    if not game.board_history or not game.state_history:
        return False

    previous_state = game.state_history.pop()
    if game.move_history:
        game.move_history.pop()
    if game.piece_history:
        game.piece_history.pop()
    if game.move_notation_history:
        game.move_notation_history.pop()

    game.board = game.board_history.pop()
    game.current_turn = previous_state["current_turn"]
    game.en_passant_target = previous_state["en_passant_target"]
    game.captured_pieces = previous_state["captured_pieces"]
    game.has_moved = previous_state["has_moved"]
    game.last_move = previous_state["last_move"]
    game.move_count = previous_state["move_count"]
    game.game_over = previous_state["game_over"]
    game.game_over_reason = previous_state.get("game_over_reason")
    game.winner = previous_state.get("winner")
    game.position_version += 1
    return True
