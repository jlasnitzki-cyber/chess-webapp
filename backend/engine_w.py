import random
import time

import config_w
import moves_w
import state_w


transposition_table = {}
killer_moves = {}
history_heuristic = {}
principal_variation_move = None
nodes = 0

TT_EXACT = "exact"
TT_LOWER = "lower"
TT_UPPER = "upper"


class SearchTimeout(Exception):
    pass


def reset_search_state_w():
    global transposition_table, principal_variation_move, nodes

    principal_variation_move = None
    transposition_table = {}
    nodes = 0


def get_book_move():

    history = tuple(state_w.move_history)

    if history in config_w.opening_book:
        book_entry = config_w.opening_book[history]
        if isinstance(book_entry, list):
            return random.choice(book_entry)
        return book_entry

    return None


def bot_evaluate_board(board):
    score = 0
    for r in range(8):
        for c in range(8):
            piece = board[r][c]
            if piece == 0:
                continue

            piece_type = abs(piece)
            table = config_w.piece_tables[piece_type]

            if piece > 0:
                score += config_w.bot_piece_values[piece_type] + table[r][c]
            else:
                score -= config_w.bot_piece_values[piece_type] + table[7 - r][c]

    return score


def get_best_move(color=None):
    if color is None:
        color = state_w.current_turn_color()

    book_move = get_book_move() if color == 'black' else None

    if book_move:
        print("Book move")
        state_w.make_move(*book_move)
        return

    move = iterative_deepening(state_w.board, state_w.bot_time_limit_ms, color)

    if move is not None:
        state_w.make_move(*move)


def move_order_score(board, move, depth=None):

    score = 0

    if move == principal_variation_move:
        score += 100000

    if depth is not None:
        killers = killer_moves.get(depth, [])
        if move in killers:
            score += 5000

    start_row, start_col, end_row, end_col = move

    attacker = abs(board[start_row][start_col])
    victim = abs(board[end_row][end_col])

    if (
        attacker == 6
        and victim == 0
        and abs(end_col - start_col) == 1
        and (end_row, end_col) == state_w.en_passant_target
    ):
        victim = 6

    if victim:
        victim_value = config_w.bot_piece_values[victim]
        attacker_value = config_w.bot_piece_values[attacker]
        score += 1000 + 10 * victim_value - attacker_value
    else:
        score += history_heuristic.get(move, 0)

    if attacker == 6 and end_row in (0, 7):
        score += config_w.bot_piece_values[2]

    return score


def transposition_key(board, maximising_player):
    return (
        tuple(tuple(row) for row in board),
        maximising_player,
        tuple(sorted(state_w.has_moved)),
        state_w.en_passant_target,
    )


def get_transposition_score(key, depth, alpha, beta):
    entry = transposition_table.get(key)

    if entry is None or entry["depth"] < depth:
        return None

    score = entry["score"]
    flag = entry["flag"]

    if flag == TT_EXACT:
        return score
    if flag == TT_LOWER and score >= beta:
        return score
    if flag == TT_UPPER and score <= alpha:
        return score

    return None


def store_transposition(key, depth, score, flag):
    previous_entry = transposition_table.get(key)
    if previous_entry is None or depth >= previous_entry["depth"]:
        transposition_table[key] = {
            "score": score,
            "depth": depth,
            "flag": flag,
        }


def bound_flag(score, alpha, beta):
    if score <= alpha:
        return TT_UPPER
    if score >= beta:
        return TT_LOWER
    return TT_EXACT


def check_search_time(deadline):
    if deadline is not None and time.perf_counter() >= deadline:
        raise SearchTimeout()


def find_best_move(board, depth, color, deadline):

    legal_moves = moves_w.get_all_legal_moves(board, color)

    if not legal_moves:
        return None, None

    legal_moves.sort(
        key=lambda move: move_order_score(board, move, depth),
        reverse=True,
    )

    maximising_engine = color == 'white'
    best_score = float('-inf') if maximising_engine else float('inf')
    best_move = None

    for move in legal_moves:
        check_search_time(deadline)

        temp_board = moves_w.simulate_move(
            board,
            move[0],
            move[1],
            move[2],
            move[3]
        )

        score = alphabeta(
            temp_board,
            depth - 1,
            float('-inf'),
            float('inf'),
            color == 'black',
            deadline,
        )

        if (
            (maximising_engine and score > best_score)
            or (not maximising_engine and score < best_score)
        ):
            best_score = score
            best_move = move

    return best_move, best_score


def fallback_move(board, color):
    legal_moves = moves_w.get_all_legal_moves(board, color)
    if not legal_moves:
        return None

    legal_moves.sort(
        key=lambda move: move_order_score(board, move),
        reverse=True,
    )
    return legal_moves[0]


def iterative_deepening(board, time_limit_ms, color):

    global nodes
    global principal_variation_move

    transposition_table.clear()
    nodes = 0

    deadline = time.perf_counter() + max(time_limit_ms, 50) / 1000
    best_move = fallback_move(board, color)
    depth = 1

    while True:
        try:
            move, score = find_best_move(board, depth, color, deadline)
        except SearchTimeout:
            print(f"Time limit reached at depth {depth}")
            break

        if move is None:
            break

        if move is not None:
            best_move = move
            principal_variation_move = move

        print(
            f"Depth {depth}: "
            f"Move={move} "
            f"Score={score}"
        )

        depth += 1

    return best_move


def alphabeta(board, depth, alpha, beta, maximising_player, deadline):
    check_search_time(deadline)

    key = transposition_key(board, maximising_player)
    cached_score = get_transposition_score(key, depth, alpha, beta)

    if cached_score is not None:
        return cached_score

    alpha_start = alpha
    beta_start = beta
    global nodes
    nodes += 1
    if depth == 0:
        value = bot_evaluate_board(board)
        store_transposition(key, depth, value, TT_EXACT)
        return value

    if maximising_player:

        legal_moves = moves_w.get_all_legal_moves(board, 'white')

        if not legal_moves:

            if moves_w.is_in_check(board, 'white'):
                value = -100000 - depth
            else:
                value = 0

            store_transposition(key, depth, value, TT_EXACT)
            return value

        value = float('-inf')

        legal_moves.sort(key=lambda move: move_order_score(board, move, depth), reverse=True)

        for move in legal_moves:
            temp_board = moves_w.simulate_move(board, move[0], move[1], move[2], move[3])

            value = max(value, alphabeta(temp_board, depth - 1, alpha, beta, False, deadline))

            alpha = max(alpha, value)

            if beta <= alpha:
                killers = killer_moves.setdefault(depth, [])
                if move not in killers:
                    killers.insert(0, move)
                    del killers[2:]

                history_heuristic[move] = history_heuristic.get(move, 0) + depth * depth
                break

        store_transposition(
            key,
            depth,
            value,
            bound_flag(value, alpha_start, beta_start),
        )

        return value
    else:
        legal_moves = moves_w.get_all_legal_moves(board, 'black')

        if not legal_moves:

            if moves_w.is_in_check(board, 'black'):
                value = 100000 + depth
            else:
                value = 0

            store_transposition(key, depth, value, TT_EXACT)
            return value

        value = float('inf')

        legal_moves.sort(key=lambda move: move_order_score(board, move, depth), reverse=True)

        for move in legal_moves:
            temp_board = moves_w.simulate_move(board, move[0], move[1], move[2], move[3])

            value = min(value, alphabeta(temp_board, depth - 1, alpha, beta, True, deadline))

            beta = min(beta, value)

            if beta <= alpha:
                killers = killer_moves.setdefault(depth, [])
                if move not in killers:
                    killers.insert(0, move)
                    del killers[2:]

                history_heuristic[move] = history_heuristic.get(move, 0) + depth * depth
                break
    store_transposition(
        key,
        depth,
        value,
        bound_flag(value, alpha_start, beta_start),
    )

    return value
