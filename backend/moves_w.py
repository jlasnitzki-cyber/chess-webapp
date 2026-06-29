import config_w
import state_w


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


def pawn_moves(board, row, col):
    moves = []
    piece = board[row][col]
    if piece == 0:
        return moves
    if piece > 0:
        direction = -1
    else:
        direction = 1

    if in_bounds(row + direction, col) and board[row + direction][col] == 0:
        moves.append((row + direction, col))
    if row == 6 and piece > 0:
        if in_bounds(row + 2 * direction, col) and board[row + 2 * direction][col] == 0:
            if board[row + direction][col] == 0:
                moves.append((row + 2 * direction, col))
    elif row == 1 and piece < 0:
        if in_bounds(row + 2 * direction, col) and board[row + 2 * direction][col] == 0:
            if board[row + direction][col] == 0:
                moves.append((row + 2 * direction, col))

    for dc in [-1, 1]:
        if in_bounds(row + direction, col + dc) and is_enemy(piece, board[row + direction][col + dc]):
            moves.append((row + direction, col + dc))

    for dc in [-1, 1]:
        new_row = row + direction
        new_col = col + dc

        if (new_row, new_col) == state_w.en_passant_target:
            adjacent_piece = board[row][new_col]

            if adjacent_piece != 0:
                if is_enemy(piece, adjacent_piece):
                    if abs(adjacent_piece) == 6:
                        moves.append((new_row, new_col))
    return moves


def knight_moves(board, row, col):
    moves = []
    piece = board[row][col]
    if piece == 0:
        return moves
    if piece > 0:
        color = 'white'
    else:
        color = 'black'
    knight_moves = [
        (2, 1), (2, -1), (-2, 1), (-2, -1),
        (1, 2), (1, -2), (-1, 2), (-1, -2)
    ]
    for dr, dc in knight_moves:
        new_row, new_col = row + dr, col + dc
        if in_bounds(new_row, new_col):
            target_piece = board[new_row][new_col]
            if target_piece == 0 or is_enemy(piece, target_piece):
                moves.append((new_row, new_col))
    return moves


def bishop_moves(board, row, col):
    moves = []
    piece = board[row][col]
    if piece == 0:
        return moves
    if piece > 0:
        color = 'white'
    else:
        color = 'black'
    directions = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
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


def rook_moves(board, row, col):
    moves = []
    piece = board[row][col]
    if piece == 0:
        return moves
    if piece > 0:
        color = 'white'
    else:
        color = 'black'
    directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
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


def queen_moves(board, row, col):
    moves = []
    piece = board[row][col]
    if piece == 0:
        return moves
    if piece > 0:
        color = 'white'
    else:
        color = 'black'
    directions = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]
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


def king_moves(board, row, col):
    moves = []
    piece = board[row][col]
    if piece == 0:
        return moves
    if piece > 0:
        color = 'white'
    else:
        color = 'black'
    directions = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]
    for dr, dc in directions:
        new_row, new_col = row + dr, col + dc
        if in_bounds(new_row, new_col):
            target_piece = board[new_row][new_col]
            if target_piece == 0 or is_enemy(piece, target_piece):
                moves.append((new_row, new_col))
    if check_castling(board, color, king_side=True):
        moves.append((row, 6))
    if check_castling(board, color, king_side=False):
        moves.append((row, 2))
    return moves


def get_moves(board, row, col):
    piece = board[row][col]

    if piece == 0:
        return []

    piece_type = config_w.piece_num(piece)

    if piece_type == 1:
        return king_moves(board, row, col)
    elif piece_type == 2:
        return queen_moves(board, row, col)
    elif piece_type == 3:
        return bishop_moves(board, row, col)
    elif piece_type == 4:
        return knight_moves(board, row, col)
    elif piece_type == 5:
        return rook_moves(board, row, col)
    elif piece_type == 6:
        return pawn_moves(board, row, col)

    return []


def is_square_attacked(board, row, col, attacker_color=None):
    piece = board[row][col]

    if attacker_color is None:
        if piece == 0:
            return False
        attacker_sign = -1 if piece > 0 else 1
    else:
        attacker_sign = 1 if attacker_color == 'white' else -1

    pawn_direction = -1 if attacker_sign > 0 else 1
    for dc in (-1, 1):
        pawn_row = row - pawn_direction
        pawn_col = col - dc
        if in_bounds(pawn_row, pawn_col) and board[pawn_row][pawn_col] == 6 * attacker_sign:
            return True

    knight_offsets = [
        (2, 1), (2, -1), (-2, 1), (-2, -1),
        (1, 2), (1, -2), (-1, 2), (-1, -2)
    ]
    for dr, dc in knight_offsets:
        attack_row = row + dr
        attack_col = col + dc
        if in_bounds(attack_row, attack_col) and board[attack_row][attack_col] == 4 * attacker_sign:
            return True

    bishop_directions = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
    for dr, dc in bishop_directions:
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

    rook_directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    for dr, dc in rook_directions:
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

    king_directions = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]
    for dr, dc in king_directions:
        attack_row = row + dr
        attack_col = col + dc
        if in_bounds(attack_row, attack_col) and board[attack_row][attack_col] == attacker_sign:
            return True

    return False


def find_king(board, color):
    king_value = 1 if color == 'white' else -1
    for r in range(8):
        for c in range(8):
            if board[r][c] == king_value:
                return (r, c)
    return None


def is_in_check(board, color):
    king_pos = find_king(board, color)
    if king_pos is None:
        return False
    return is_square_attacked(board, king_pos[0], king_pos[1])


def copy_board(board):
    return [row[:] for row in board]


def apply_special_moves(board, start_row, start_col, end_row, end_col):
    """
    Applies a move to `board` in place, including special-move side effects
    (en passant capture, castling rook move, pawn promotion).
    Returns (captured_piece, new_en_passant_target).
    """
    piece = board[start_row][start_col]
    captured_piece = board[end_row][end_col]

    if abs(piece) == 6 and abs(end_col - start_col) == 1 and board[end_row][end_col] == 0:
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


def simulate_move(board, start_row, start_col, end_row, end_col):
    new_board = copy_board(board)
    apply_special_moves(new_board, start_row, start_col, end_row, end_col)
    return new_board


def is_legal_move(board, start_row, start_col, end_row, end_col):
    piece = board[start_row][start_col]
    if piece == 0:
        return False
    color = 'white' if piece > 0 else 'black'
    new_board = simulate_move(board, start_row, start_col, end_row, end_col)
    return not is_in_check(new_board, color)


def get_legal_moves(board, row, col):
    legal_moves = []
    for move in get_moves(board, row, col):
        if is_legal_move(board, row, col, move[0], move[1]):
            legal_moves.append(move)
    return legal_moves


def get_all_legal_moves(board, color):
    all_moves = []

    color_sign = 1 if color == 'white' else -1

    for row in range(8):
        for col in range(8):
            piece = board[row][col]

            if piece * color_sign > 0:
                legal_moves = get_legal_moves(board, row, col)

                for move in legal_moves:
                    all_moves.append(
                        (row, col, move[0], move[1])
                    )
    return all_moves


def get_captures(board, color):
    captures = []
    legal_moves = get_all_legal_moves(board, color)

    for move in legal_moves:
        if board[move[2]][move[3]] != 0:
            captures.append(move[0], move[1])

    return captures


def check_endgame(board, color):

    for r in range(8):
        for c in range(8):

            piece = board[r][c]

            if piece * (1 if color == 'white' else -1) > 0:

                if get_legal_moves(board, r, c):
                    end = None
                    return end

    if is_in_check(board, color):
        print(f"{color} is in checkmate!")
        end = 'checkmate'
    else:
        print(f"{color} is in stalemate!")
        end = 'stalemate'

    return end


def check_castling(board, color, king_side):
    row = 7 if color == 'white' else 0
    king_col = 4
    rook_col = 7 if king_side else 0
    king_value = 1 if color == 'white' else -1
    rook_value = 5 if color == 'white' else -5

    if f'{color}_king' in state_w.has_moved:
        return False
    if f'{color}_rook_{rook_col}' in state_w.has_moved:
        return False

    if board[row][king_col] != king_value or board[row][rook_col] != rook_value:
        return False

    step = 1 if rook_col > king_col else -1
    for col in range(king_col + step, rook_col, step):
        if board[row][col] != 0:
            return False

    opponent_color = 'black' if color == 'white' else 'white'
    dest_col = 6 if king_side else 2
    for col in range(king_col, dest_col + step, step):
        if is_square_attacked(board, row, col, opponent_color):
            return False

    return True


def check_pawn_promotion(board, row, col):
    piece = board[row][col]
    if piece == 0:
        return False
    if piece > 0 and row == 0:
        return True
    elif piece < 0 and row == 7:
        return True
    return False
