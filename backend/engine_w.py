import copy
import random
import time
from dataclasses import dataclass, field

import config_w
import moves_w
import state_w


TT_EXACT = "exact"
TT_LOWER = "lower"
TT_UPPER = "upper"
MATE_SCORE = 100000
MAX_SEARCH_DEPTH = 64

PIECE_TO_ZOBRIST_INDEX = {
    1: 0,
    2: 1,
    3: 2,
    4: 3,
    5: 4,
    6: 5,
    -1: 6,
    -2: 7,
    -3: 8,
    -4: 9,
    -5: 10,
    -6: 11,
}

_zobrist_rng = random.Random(20260630)
ZOBRIST_PIECES = [
    [_zobrist_rng.getrandbits(64) for _ in range(64)] for _ in range(12)
]
ZOBRIST_SIDE = _zobrist_rng.getrandbits(64)
ZOBRIST_EP_FILES = [_zobrist_rng.getrandbits(64) for _ in range(8)]
ZOBRIST_CASTLING = {
    "white_king": _zobrist_rng.getrandbits(64),
    "black_king": _zobrist_rng.getrandbits(64),
    "white_rook_0": _zobrist_rng.getrandbits(64),
    "white_rook_7": _zobrist_rng.getrandbits(64),
    "black_rook_0": _zobrist_rng.getrandbits(64),
    "black_rook_7": _zobrist_rng.getrandbits(64),
}


class SearchTimeout(Exception):
    pass


@dataclass
class SearchContext:
    transposition_table: dict = field(default_factory=dict)
    killer_moves: dict = field(default_factory=dict)
    history_heuristic: dict = field(default_factory=dict)
    principal_variation_move: tuple | None = None
    nodes: int = 0
    deadline: float | None = None
    cancelled: bool = False


def opponent(color):
    return "black" if color == "white" else "white"


def color_sign(color):
    return 1 if color == "white" else -1


def check_search_time(context):
    if context.cancelled:
        raise SearchTimeout()
    if context.deadline is not None and time.perf_counter() >= context.deadline:
        raise SearchTimeout()


def get_book_move(game, color):
    history = tuple(game.move_history)
    book_entry = config_w.opening_book.get(history)
    if book_entry is None:
        return None

    move = random.choice(book_entry) if isinstance(book_entry, list) else book_entry
    legal_moves = moves_w.get_all_legal_moves(game, color)
    return move if move in legal_moves else None


def game_phase(board):
    phase = 0
    weights = {2: 4, 5: 2, 3: 1, 4: 1}
    for row in board:
        for piece in row:
            phase += weights.get(abs(piece), 0)
    return min(24, phase) / 24


def table_value(piece, row, col, endgame_weight):
    piece_type = abs(piece)

    if piece_type == 1:
        middle_table = config_w.king_table
        end_table = config_w.king_endgame_table
        if piece > 0:
            return (middle_table[row][col] * (1 - endgame_weight)) + (
                end_table[row][col] * endgame_weight
            )
        return (middle_table[7 - row][col] * (1 - endgame_weight)) + (
            end_table[7 - row][col] * endgame_weight
        )

    table = config_w.piece_tables[piece_type]
    return table[row][col] if piece > 0 else table[7 - row][col]


def is_passed_pawn(row, col, sign, enemy_pawns):
    files = (col - 1, col, col + 1)
    for pawn_row, pawn_col in enemy_pawns:
        if pawn_col not in files:
            continue
        if sign > 0 and pawn_row < row:
            return False
        if sign < 0 and pawn_row > row:
            return False
    return True


def knight_outpost(board, row, col, sign):
    support_row = row + (1 if sign > 0 else -1)
    supported = False
    for support_col in (col - 1, col + 1):
        if (
            moves_w.in_bounds(support_row, support_col)
            and board[support_row][support_col] == 6 * sign
        ):
            supported = True

    if not supported:
        return False

    enemy_sign = -sign
    enemy_attack_row = row + (1 if sign > 0 else -1)
    for attack_col in (col - 1, col + 1):
        if (
            moves_w.in_bounds(enemy_attack_row, attack_col)
            and board[enemy_attack_row][attack_col] == 6 * enemy_sign
        ):
            return False
    return True


def king_safety(board, color, king_pos, middle_game_weight, pawn_files):
    if king_pos is None or middle_game_weight <= 0:
        return 0

    sign = color_sign(color)
    row, col = king_pos
    front = -1 if sign > 0 else 1
    safety = 0

    for file_col in (col - 1, col, col + 1):
        if not 0 <= file_col < 8:
            continue

        shield_found = False
        for distance in (1, 2):
            shield_row = row + front * distance
            if (
                moves_w.in_bounds(shield_row, file_col)
                and board[shield_row][file_col] == 6 * sign
            ):
                shield_found = True
                break

        safety += 3 if shield_found else -4
        if not pawn_files[color][file_col]:
            safety -= 4

    return int(safety * middle_game_weight)


def pawn_structure_score(color, pawns, enemy_pawns, pawn_files):
    sign = color_sign(color)
    score = 0

    for file_pawns in pawn_files[color]:
        if len(file_pawns) > 1:
            score -= 4 * (len(file_pawns) - 1)

    for row, col in pawns:
        isolated = True
        for adjacent_file in (col - 1, col + 1):
            if 0 <= adjacent_file < 8 and pawn_files[color][adjacent_file]:
                isolated = False
        if isolated:
            score -= 3

        if is_passed_pawn(row, col, sign, enemy_pawns):
            advance = 6 - row if sign > 0 else row - 1
            score += 4 + max(0, advance) * 2

    return score


def positional_features(
    board, pawn_files, pawns, king_positions, middle_game_weight, endgame_weight
):
    score = 0

    for color in ("white", "black"):
        sign = color_sign(color)
        enemy = opponent(color)
        feature = pawn_structure_score(
            color, pawns[color], pawns[enemy], pawn_files
        )
        feature += king_safety(
            board, color, king_positions[color], middle_game_weight, pawn_files
        )

        bishops = 0
        for row in range(8):
            for col in range(8):
                piece = board[row][col]
                if piece * sign <= 0:
                    continue

                piece_type = abs(piece)
                if piece_type == 3:
                    bishops += 1
                elif piece_type == 4 and knight_outpost(board, row, col, sign):
                    feature += 5
                elif piece_type == 5:
                    own_file_pawns = len(pawn_files[color][col])
                    enemy_file_pawns = len(pawn_files[enemy][col])
                    if own_file_pawns == 0 and enemy_file_pawns == 0:
                        feature += 5
                    elif own_file_pawns == 0:
                        feature += 2
                    if (color == "white" and row == 1) or (
                        color == "black" and row == 6
                    ):
                        feature += 4

        if bishops >= 2:
            feature += 4

        score += feature * sign

    return int(score * (0.75 + 0.25 * endgame_weight))


def bot_evaluate_board(board):
    score = 0
    middle_game_weight = game_phase(board)
    endgame_weight = 1 - middle_game_weight
    pawn_files = {
        "white": [[] for _ in range(8)],
        "black": [[] for _ in range(8)],
    }
    pawns = {"white": [], "black": []}
    king_positions = {"white": None, "black": None}

    for row in range(8):
        for col in range(8):
            piece = board[row][col]
            if piece == 0:
                continue

            sign = 1 if piece > 0 else -1
            color = "white" if piece > 0 else "black"
            piece_type = abs(piece)

            score += sign * (
                config_w.bot_piece_values[piece_type]
                + table_value(piece, row, col, endgame_weight)
            )

            if piece_type == 6:
                pawns[color].append((row, col))
                pawn_files[color][col].append(row)
            elif piece_type == 1:
                king_positions[color] = (row, col)

    score += positional_features(
        board,
        pawn_files,
        pawns,
        king_positions,
        middle_game_weight,
        endgame_weight,
    )
    return int(score)


def evaluate_for_color(game, color):
    return bot_evaluate_board(game.board) * color_sign(color)


def captured_piece_for_move(game, move):
    start_row, start_col, end_row, end_col = move
    piece = game.board[start_row][start_col]
    captured_piece = game.board[end_row][end_col]

    if (
        abs(piece) == 6
        and captured_piece == 0
        and abs(end_col - start_col) == 1
        and (end_row, end_col) == game.en_passant_target
    ):
        captured_piece = game.board[start_row][end_col]

    return captured_piece


def move_order_score(game, move, context, depth=None, tt_move=None):
    score = 0

    if move == tt_move or move == context.principal_variation_move:
        score += 100000

    if depth is not None:
        killers = context.killer_moves.get(depth, [])
        if move in killers:
            score += 5000

    start_row, start_col, end_row, _ = move
    attacker = abs(game.board[start_row][start_col])
    victim = abs(captured_piece_for_move(game, move))

    if victim:
        victim_value = config_w.bot_piece_values[victim]
        attacker_value = config_w.bot_piece_values[attacker]
        score += 1000 + 10 * victim_value - attacker_value
    else:
        score += context.history_heuristic.get(move, 0)

    if attacker == 6 and end_row in (0, 7):
        score += config_w.bot_piece_values[2]

    return score


def zobrist_key(game, color_to_move):
    key = 0

    for row in range(8):
        for col in range(8):
            piece = game.board[row][col]
            if piece:
                key ^= ZOBRIST_PIECES[PIECE_TO_ZOBRIST_INDEX[piece]][row * 8 + col]

    if color_to_move == "black":
        key ^= ZOBRIST_SIDE

    if game.en_passant_target is not None:
        key ^= ZOBRIST_EP_FILES[game.en_passant_target[1]]

    for moved_key in game.has_moved:
        zobrist_value = ZOBRIST_CASTLING.get(moved_key)
        if zobrist_value is not None:
            key ^= zobrist_value

    return key


def transposition_lookup(context, key, depth, alpha, beta):
    entry = context.transposition_table.get(key)
    if entry is None:
        return None, None

    tt_move = entry.get("best_move")
    if entry["depth"] < depth:
        return None, tt_move

    score = entry["score"]
    flag = entry["flag"]

    if flag == TT_EXACT:
        return score, tt_move
    if flag == TT_LOWER and score >= beta:
        return score, tt_move
    if flag == TT_UPPER and score <= alpha:
        return score, tt_move

    return None, tt_move


def store_transposition(context, key, depth, score, flag, best_move):
    previous_entry = context.transposition_table.get(key)
    if previous_entry is None or depth >= previous_entry["depth"]:
        context.transposition_table[key] = {
            "score": score,
            "depth": depth,
            "flag": flag,
            "best_move": best_move,
        }


def bound_flag(score, alpha, beta):
    if score <= alpha:
        return TT_UPPER
    if score >= beta:
        return TT_LOWER
    return TT_EXACT


def make_search_move(game, move):
    start_row, start_col, end_row, end_col = move
    piece = game.board[start_row][start_col]
    previous_en_passant = game.en_passant_target
    previous_has_moved = set(game.has_moved)
    captured_square = (end_row, end_col)
    captured_piece = game.board[end_row][end_col]
    rook_move = None

    if (
        abs(piece) == 6
        and captured_piece == 0
        and abs(end_col - start_col) == 1
        and (end_row, end_col) == game.en_passant_target
    ):
        captured_square = (start_row, end_col)
        captured_piece = game.board[start_row][end_col]

    if abs(piece) == 1 and abs(end_col - start_col) == 2:
        rook_move = (
            start_row,
            7 if end_col == 6 else 0,
            start_row,
            5 if end_col == 6 else 3,
        )

    captured_piece_from_apply, new_en_passant = moves_w.apply_special_moves(
        game.board,
        start_row,
        start_col,
        end_row,
        end_col,
        game.en_passant_target,
    )

    state_w.update_castling_rights(
        game,
        piece,
        start_row,
        start_col,
        end_col,
        captured_piece,
        captured_square[0],
        captured_square[1],
    )
    game.en_passant_target = new_en_passant

    return {
        "move": move,
        "piece": piece,
        "captured_piece": captured_piece_from_apply
        if captured_piece == 0
        else captured_piece,
        "captured_square": captured_square,
        "rook_move": rook_move,
        "previous_en_passant": previous_en_passant,
        "previous_has_moved": previous_has_moved,
    }


def unmake_search_move(game, context):
    start_row, start_col, end_row, end_col = context["move"]
    captured_square = context["captured_square"]
    captured_piece = context["captured_piece"]
    rook_move = context["rook_move"]

    game.board[start_row][start_col] = context["piece"]
    game.board[end_row][end_col] = 0

    if captured_square == (end_row, end_col):
        game.board[end_row][end_col] = captured_piece
    else:
        game.board[captured_square[0]][captured_square[1]] = captured_piece

    if rook_move is not None:
        rook_start_row, rook_start_col, rook_end_row, rook_end_col = rook_move
        game.board[rook_start_row][rook_start_col] = game.board[rook_end_row][
            rook_end_col
        ]
        game.board[rook_end_row][rook_end_col] = 0

    game.en_passant_target = context["previous_en_passant"]
    game.has_moved = context["previous_has_moved"]


def ordered_legal_moves(game, color, context, depth, tt_move=None):
    legal_moves = moves_w.get_all_legal_moves(game, color)
    legal_moves.sort(
        key=lambda move: move_order_score(game, move, context, depth, tt_move),
        reverse=True,
    )
    return legal_moves


def capture_moves(game, color, context, depth):
    captures = []
    for move in moves_w.get_all_legal_moves(game, color):
        if captured_piece_for_move(game, move) != 0 or (
            abs(game.board[move[0]][move[1]]) == 6 and move[2] in (0, 7)
        ):
            captures.append(move)

    captures.sort(
        key=lambda move: move_order_score(game, move, context, depth),
        reverse=True,
    )
    return captures


def quiescence(game, alpha, beta, color, context, ply):
    check_search_time(context)

    stand_pat = evaluate_for_color(game, color)
    if stand_pat >= beta:
        return beta
    if alpha < stand_pat:
        alpha = stand_pat

    for move in capture_moves(game, color, context, 0):
        move_context = make_search_move(game, move)
        try:
            score = -quiescence(game, -beta, -alpha, opponent(color), context, ply + 1)
        finally:
            unmake_search_move(game, move_context)

        if score >= beta:
            return beta
        if score > alpha:
            alpha = score

    return alpha


def negamax(game, depth, alpha, beta, color, context, ply=0):
    check_search_time(context)
    context.nodes += 1

    alpha_start = alpha
    key = zobrist_key(game, color)
    cached_score, tt_move = transposition_lookup(context, key, depth, alpha, beta)
    if cached_score is not None:
        return cached_score

    if depth == 0:
        value = quiescence(game, alpha, beta, color, context, ply)
        store_transposition(context, key, depth, value, TT_EXACT, None)
        return value

    legal_moves = ordered_legal_moves(game, color, context, depth, tt_move)
    if not legal_moves:
        value = -MATE_SCORE + ply if moves_w.is_in_check(game, color) else 0
        store_transposition(context, key, depth, value, TT_EXACT, None)
        return value

    best_score = float("-inf")
    best_move = None

    for index, move in enumerate(legal_moves):
        move_context = make_search_move(game, move)
        try:
            if index == 0:
                score = -negamax(
                    game, depth - 1, -beta, -alpha, opponent(color), context, ply + 1
                )
            else:
                score = -negamax(
                    game,
                    depth - 1,
                    -alpha - 1,
                    -alpha,
                    opponent(color),
                    context,
                    ply + 1,
                )
                if alpha < score < beta:
                    score = -negamax(
                        game,
                        depth - 1,
                        -beta,
                        -alpha,
                        opponent(color),
                        context,
                        ply + 1,
                    )
        finally:
            unmake_search_move(game, move_context)

        if score > best_score:
            best_score = score
            best_move = move

        if score > alpha:
            alpha = score

        if alpha >= beta:
            if captured_piece_for_move(game, move) == 0:
                killers = context.killer_moves.setdefault(depth, [])
                if move not in killers:
                    killers.insert(0, move)
                    del killers[2:]
                context.history_heuristic[move] = (
                    context.history_heuristic.get(move, 0) + depth * depth
                )
            break

    store_transposition(
        context,
        key,
        depth,
        best_score,
        bound_flag(best_score, alpha_start, beta),
        best_move,
    )
    return best_score


def find_best_move(game, depth, color, context):
    legal_moves = ordered_legal_moves(
        game, color, context, depth, context.principal_variation_move
    )
    if not legal_moves:
        return None, None

    best_score = float("-inf")
    best_move = None
    alpha = float("-inf")
    beta = float("inf")

    for index, move in enumerate(legal_moves):
        check_search_time(context)
        move_context = make_search_move(game, move)
        try:
            if index == 0:
                score = -negamax(game, depth - 1, -beta, -alpha, opponent(color), context, 1)
            else:
                score = -negamax(
                    game, depth - 1, -alpha - 1, -alpha, opponent(color), context, 1
                )
                if alpha < score < beta:
                    score = -negamax(
                        game, depth - 1, -beta, -alpha, opponent(color), context, 1
                    )
        finally:
            unmake_search_move(game, move_context)

        if score > best_score:
            best_score = score
            best_move = move

        if score > alpha:
            alpha = score

    return best_move, best_score


def fallback_move(game, color, context):
    legal_moves = ordered_legal_moves(game, color, context, 0)
    return legal_moves[0] if legal_moves else None


def iterative_deepening(game, time_limit_ms, color, depth_limit=None):
    context = SearchContext()
    context.deadline = (
        None
        if depth_limit is not None
        else time.perf_counter() + max(time_limit_ms, 50) / 1000
    )
    max_depth = depth_limit if depth_limit is not None else MAX_SEARCH_DEPTH
    best_move = fallback_move(game, color, context)
    saved_board = copy.deepcopy(game.board)
    saved_en_passant = game.en_passant_target
    saved_has_moved = set(game.has_moved)

    try:
        for depth in range(1, max_depth + 1):
            try:
                move, score = find_best_move(game, depth, color, context)
            except SearchTimeout:
                break

            if move is None:
                break

            best_move = move
            context.principal_variation_move = move
            print(f"Depth {depth}: Move={move} Score={score} Nodes={context.nodes}")
    finally:
        game.board = saved_board
        game.en_passant_target = saved_en_passant
        game.has_moved = saved_has_moved

    return best_move, context


def find_best_engine_move(game, color=None):
    color = color or game.current_turn_color()
    book_move = get_book_move(game, color)
    if book_move:
        return book_move, SearchContext()

    depth_limit = game.bot_depth_limit if game.bot_limit_mode == "depth" else None
    return iterative_deepening(game, game.bot_time_limit_ms, color, depth_limit)
