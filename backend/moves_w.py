import config_w


is_enemy = lambda x, y: (x * y) < 0


def print_board(board):
    for row in board:
        print(row)


def move_piece(board, start_row, start_col, end_row, end_col):
    piece = board[start_row][start_col]
    board[end_row][end_col] = piece
    board[start_row][start_col] = 0


def in_bounds(row, col):
    return 0 <= row < 8 and 0 <= col < 8


def pawn_moves(game, row, col):
    board = game.board
    moves = []
    piece = board[row][col]
    if piece == 0:
        return moves

    direction = -1 if piece > 0 else 1

    if in_bounds(row + direction, col) and board[row + direction][col] == 0:
        moves.append((row + direction, col))

    if row == 6 and piece > 0:
        if (
            in_bounds(row + 2 * direction, col)
            and board[row + direction][col] == 0
            and board[row + 2 * direction][col] == 0
        ):
            moves.append((row + 2 * direction, col))
    elif row == 1 and piece < 0:
        if (
            in_bounds(row + 2 * direction, col)
            and board[row + direction][col] == 0
            and board[row + 2 * direction][col] == 0
        ):
            moves.append((row + 2 * direction, col))

    for dc in (-1, 1):
        capture_row = row + direction
        capture_col = col + dc
        if in_bounds(capture_row, capture_col) and is_enemy(
            piece, board[capture_row][capture_col]
        ):
            moves.append((capture_row, capture_col))

    for dc in (-1, 1):
        new_row = row + direction
        new_col = col + dc
        if (new_row, new_col) == game.en_passant_target:
            adjacent_piece = board[row][new_col]
            if adjacent_piece != 0 and is_enemy(piece, adjacent_piece):
                if abs(adjacent_piece) == 6:
                    moves.append((new_row, new_col))

    return moves


def knight_moves(game, row, col):
    board = game.board
    moves = []
    piece = board[row][col]
    if piece == 0:
        return moves

    offsets = [
        (2, 1),
        (2, -1),
        (-2, 1),
        (-2, -1),
        (1, 2),
        (1, -2),
        (-1, 2),
        (-1, -2),
    ]
    for dr, dc in offsets:
        new_row, new_col = row + dr, col + dc
        if in_bounds(new_row, new_col):
            target_piece = board[new_row][new_col]
            if target_piece == 0 or is_enemy(piece, target_piece):
                moves.append((new_row, new_col))
    return moves


def sliding_moves(game, row, col, directions):
    board = game.board
    moves = []
    piece = board[row][col]
    if piece == 0:
        return moves

    for dr, dc in directions:
        new_row, new_col = row + dr, col + dc
        while in_bounds(new_row, new_col):
            target_piece = board[new_row][new_col]
            if target_piece == 0:
                moves.append((new_row, new_col))
            elif is_enemy(piece, target_piece):
                moves.append((new_row, new_col))
                break
            else:
                break
            new_row += dr
            new_col += dc
    return moves


def bishop_moves(game, row, col):
    return sliding_moves(game, row, col, [(-1, -1), (-1, 1), (1, -1), (1, 1)])


def rook_moves(game, row, col):
    return sliding_moves(game, row, col, [(-1, 0), (1, 0), (0, -1), (0, 1)])


def queen_moves(game, row, col):
    return sliding_moves(
        game,
        row,
        col,
        [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)],
    )


def king_moves(game, row, col):
    board = game.board
    moves = []
    piece = board[row][col]
    if piece == 0:
        return moves

    color = "white" if piece > 0 else "black"
    directions = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]
    for dr, dc in directions:
        new_row, new_col = row + dr, col + dc
        if in_bounds(new_row, new_col):
            target_piece = board[new_row][new_col]
            if target_piece == 0 or is_enemy(piece, target_piece):
                moves.append((new_row, new_col))

    if check_castling(game, color, king_side=True):
        moves.append((row, 6))
    if check_castling(game, color, king_side=False):
        moves.append((row, 2))
    return moves


def get_moves(game, row, col):
    piece = game.board[row][col]
    if piece == 0:
        return []

    piece_type = config_w.piece_num(piece)
    if piece_type == 1:
        return king_moves(game, row, col)
    if piece_type == 2:
        return queen_moves(game, row, col)
    if piece_type == 3:
        return bishop_moves(game, row, col)
    if piece_type == 4:
        return knight_moves(game, row, col)
    if piece_type == 5:
        return rook_moves(game, row, col)
    if piece_type == 6:
        return pawn_moves(game, row, col)
    return []


def is_square_attacked(board, row, col, attacker_color=None):
    piece = board[row][col]

    if attacker_color is None:
        if piece == 0:
            return False
        attacker_sign = -1 if piece > 0 else 1
    else:
        attacker_sign = 1 if attacker_color == "white" else -1

    pawn_direction = -1 if attacker_sign > 0 else 1
    for dc in (-1, 1):
        pawn_row = row - pawn_direction
        pawn_col = col - dc
        if in_bounds(pawn_row, pawn_col) and board[pawn_row][pawn_col] == 6 * attacker_sign:
            return True

    knight_offsets = [
        (2, 1),
        (2, -1),
        (-2, 1),
        (-2, -1),
        (1, 2),
        (1, -2),
        (-1, 2),
        (-1, -2),
    ]
    for dr, dc in knight_offsets:
        attack_row = row + dr
        attack_col = col + dc
        if in_bounds(attack_row, attack_col) and board[attack_row][attack_col] == 4 * attacker_sign:
            return True

    for dr, dc in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
        attack_row = row + dr
        attack_col = col + dc
        while in_bounds(attack_row, attack_col):
            attacker = board[attack_row][attack_col]
            if attacker != 0:
                if attacker in (3 * attacker_sign, 2 * attacker_sign):
                    return True
                break
            attack_row += dr
            attack_col += dc

    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        attack_row = row + dr
        attack_col = col + dc
        while in_bounds(attack_row, attack_col):
            attacker = board[attack_row][attack_col]
            if attacker != 0:
                if attacker in (5 * attacker_sign, 2 * attacker_sign):
                    return True
                break
            attack_row += dr
            attack_col += dc

    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]:
        attack_row = row + dr
        attack_col = col + dc
        if in_bounds(attack_row, attack_col) and board[attack_row][attack_col] == attacker_sign:
            return True

    return False


def find_king(board, color):
    king_value = 1 if color == "white" else -1
    for row in range(8):
        for col in range(8):
            if board[row][col] == king_value:
                return (row, col)
    return None


def is_in_check(game, color):
    king_pos = find_king(game.board, color)
    if king_pos is None:
        return False
    return is_square_attacked(game.board, king_pos[0], king_pos[1])


def copy_board(board):
    return [row[:] for row in board]


def apply_special_moves(
    board, start_row, start_col, end_row, end_col, en_passant_target=None
):
    piece = board[start_row][start_col]
    captured_piece = board[end_row][end_col]

    if (
        abs(piece) == 6
        and abs(end_col - start_col) == 1
        and board[end_row][end_col] == 0
        and (end_row, end_col) == en_passant_target
    ):
        captured_piece = board[start_row][end_col]
        board[start_row][end_col] = 0

    if abs(piece) == 1 and abs(end_col - start_col) == 2:
        if end_col == 6:
            board[start_row][5] = board[start_row][7]
            board[start_row][7] = 0
        elif end_col == 2:
            board[start_row][3] = board[start_row][0]
            board[start_row][0] = 0

    board[end_row][end_col] = piece
    board[start_row][start_col] = 0

    if abs(piece) == 6 and end_row in (0, 7):
        board[end_row][end_col] = 2 * (1 if piece > 0 else -1)

    if abs(piece) == 6 and abs(start_row - end_row) == 2:
        new_en_passant_target = ((start_row + end_row) // 2, start_col)
    else:
        new_en_passant_target = None

    return captured_piece, new_en_passant_target


def simulate_move(game, start_row, start_col, end_row, end_col):
    new_board = copy_board(game.board)
    apply_special_moves(
        new_board,
        start_row,
        start_col,
        end_row,
        end_col,
        game.en_passant_target,
    )
    return new_board


def make_temporary_move(game, start_row, start_col, end_row, end_col):
    board = game.board
    piece = board[start_row][start_col]
    captured_square = (end_row, end_col)
    captured_piece = board[end_row][end_col]
    rook_move = None

    if (
        abs(piece) == 6
        and captured_piece == 0
        and abs(end_col - start_col) == 1
        and (end_row, end_col) == game.en_passant_target
    ):
        captured_square = (start_row, end_col)
        captured_piece = board[start_row][end_col]

    if abs(piece) == 1 and abs(end_col - start_col) == 2:
        rook_move = (
            start_row,
            7 if end_col == 6 else 0,
            start_row,
            5 if end_col == 6 else 3,
        )

    apply_special_moves(
        board, start_row, start_col, end_row, end_col, game.en_passant_target
    )

    return {
        "piece": piece,
        "move": (start_row, start_col, end_row, end_col),
        "captured_piece": captured_piece,
        "captured_square": captured_square,
        "rook_move": rook_move,
    }


def undo_temporary_move(game, context):
    board = game.board
    start_row, start_col, end_row, end_col = context["move"]
    captured_square = context["captured_square"]
    captured_piece = context["captured_piece"]
    rook_move = context["rook_move"]

    board[start_row][start_col] = context["piece"]
    board[end_row][end_col] = 0

    if captured_square == (end_row, end_col):
        board[end_row][end_col] = captured_piece
    else:
        board[captured_square[0]][captured_square[1]] = captured_piece

    if rook_move is not None:
        rook_start_row, rook_start_col, rook_end_row, rook_end_col = rook_move
        board[rook_start_row][rook_start_col] = board[rook_end_row][rook_end_col]
        board[rook_end_row][rook_end_col] = 0


def is_legal_move(game, start_row, start_col, end_row, end_col):
    piece = game.board[start_row][start_col]
    if piece == 0:
        return False

    if (end_row, end_col) not in get_moves(game, start_row, start_col):
        return False

    color = "white" if piece > 0 else "black"
    context = make_temporary_move(game, start_row, start_col, end_row, end_col)
    try:
        return not is_in_check(game, color)
    finally:
        undo_temporary_move(game, context)


def get_legal_moves(game, row, col):
    legal_moves = []
    for move in get_moves(game, row, col):
        if is_legal_move(game, row, col, move[0], move[1]):
            legal_moves.append(move)
    return legal_moves


def get_all_legal_moves(game, color):
    all_moves = []
    sign = 1 if color == "white" else -1

    for row in range(8):
        for col in range(8):
            piece = game.board[row][col]
            if piece * sign > 0:
                for move in get_legal_moves(game, row, col):
                    all_moves.append((row, col, move[0], move[1]))
    return all_moves


def get_captures(game, color):
    captures = []
    for move in get_all_legal_moves(game, color):
        if game.board[move[2]][move[3]] != 0:
            captures.append(move)
    return captures


def check_endgame(game, color):
    sign = 1 if color == "white" else -1

    for row in range(8):
        for col in range(8):
            piece = game.board[row][col]
            if piece * sign > 0 and get_legal_moves(game, row, col):
                return None

    return "checkmate" if is_in_check(game, color) else "stalemate"


def check_castling(game, color, king_side):
    board = game.board
    row = 7 if color == "white" else 0
    king_col = 4
    rook_col = 7 if king_side else 0
    king_value = 1 if color == "white" else -1
    rook_value = 5 if color == "white" else -5

    if f"{color}_king" in game.has_moved:
        return False
    if f"{color}_rook_{rook_col}" in game.has_moved:
        return False

    if board[row][king_col] != king_value or board[row][rook_col] != rook_value:
        return False

    step = 1 if rook_col > king_col else -1
    for col in range(king_col + step, rook_col, step):
        if board[row][col] != 0:
            return False

    opponent_color = "black" if color == "white" else "white"
    dest_col = 6 if king_side else 2
    for col in range(king_col, dest_col + step, step):
        if is_square_attacked(board, row, col, opponent_color):
            return False

    return True


def check_pawn_promotion(game, row, col):
    piece = game.board[row][col]
    if piece == 0:
        return False
    return (piece > 0 and row == 0) or (piece < 0 and row == 7)
