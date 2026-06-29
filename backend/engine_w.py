import random

import config_w
import moves_w
import state_w


transposition_table = {}
killer_moves = {}
history_heuristic = {}
principal_variation_move = None
nodes = 0


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


def get_best_move():

    book_move = get_book_move()

    if book_move:
        print("Book move")
        state_w.make_move(*book_move)
        return

    move = iterative_deepening(state_w.board, state_w.bot_search_depth)

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

    if victim:
        score += 1000 + 10 * victim - attacker
    else:
        score += history_heuristic.get(move, 0)

    return score


def find_best_move(board, depth):

    legal_moves = moves_w.get_all_legal_moves(board, 'black')

    if not legal_moves:
        return None, None

    legal_moves.sort(
        key=lambda move: move_order_score(board, move, depth)
    )

    best_score = float('inf')
    best_move = None

    for move in legal_moves:

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
            True
        )

        if score < best_score:
            best_score = score
            best_move = move

    return best_move, best_score


def iterative_deepening(board, max_depth):

    global nodes
    global principal_variation_move

    transposition_table.clear()
    nodes = 0

    best_move = None

    for depth in range(1, max_depth + 1):

        move, score = find_best_move(board, depth)

        if move is not None:
            best_move = move
            principal_variation_move = move

        print(
            f"Depth {depth}: "
            f"Move={move} "
            f"Score={score}"
        )

    return best_move


def alphabeta(board, depth, alpha, beta, maximising_player):

    key = (
        tuple(tuple(row) for row in board), depth, maximising_player)

    if key in transposition_table:
        return transposition_table[key]
    global nodes
    nodes += 1
    if depth == 0:
        value = bot_evaluate_board(board)
        transposition_table[key] = value
        return value

    if maximising_player:

        legal_moves = moves_w.get_all_legal_moves(board, 'white')

        if not legal_moves:

            if moves_w.is_in_check(board, 'white'):
                value = -100000 - depth
            else:
                value = 0

            transposition_table[key] = value
            return value

        value = float('-inf')

        legal_moves.sort(key=lambda move: move_order_score(board, move, depth), reverse=True)

        for move in legal_moves:
            temp_board = moves_w.simulate_move(board, move[0], move[1], move[2], move[3])

            value = max(value, alphabeta(temp_board, depth - 1, alpha, beta, False))

            alpha = max(alpha, value)

            if beta <= alpha:
                killers = killer_moves.setdefault(depth, [])
                if move not in killers:
                    killers.insert(0, move)
                    del killers[2:]

                history_heuristic[move] = history_heuristic.get(move, 0) + depth * depth
                break

        transposition_table[key] = value

        return value
    else:
        legal_moves = moves_w.get_all_legal_moves(board, 'black')

        if not legal_moves:

            if moves_w.is_in_check(board, 'black'):
                value = 100000 + depth
            else:
                value = 0

            transposition_table[key] = value
            return value

        value = float('inf')

        legal_moves.sort(key=lambda move: move_order_score(board, move, depth), reverse=True)

        for move in legal_moves:
            temp_board = moves_w.simulate_move(board, move[0], move[1], move[2], move[3])

            value = min(value, alphabeta(temp_board, depth - 1, alpha, beta, True))

            beta = min(beta, value)

            if beta <= alpha:
                killers = killer_moves.setdefault(depth, [])
                if move not in killers:
                    killers.insert(0, move)
                    del killers[2:]

                history_heuristic[move] = history_heuristic.get(move, 0) + depth * depth
                break
    transposition_table[key] = value

    return value
