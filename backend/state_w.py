import copy

import config_w


initial_board = copy.deepcopy(config_w.board_start)
board = copy.deepcopy(initial_board)

board_history = []
move_history = []
piece_history = []
move_notation_history = []

en_passant_target = None
current_turn = 1
selected_square = None
move_count = 0
game_over = False
bot_search_depth = 3
menu_active = True
running = True

king_moved = False
rook_moved = False
has_moved = set()

captured_pieces = {'white': [], 'black': []}
last_move = None
eval = None


def evaluation(captured_pieces):
    white_values = []
    for piece in captured_pieces['white']:
        white_values.append(config_w.piece_values[abs(piece)])

    black_values = []
    for piece in captured_pieces['black']:
        black_values.append(config_w.piece_values[abs(piece)] * -1)

    eval = (sum(white_values) + sum(black_values))

    return eval


def undo_move():
    global board, current_turn, last_move

    if board_history:
        if move_history:
            move_history.pop()
        if piece_history:
            piece_history.pop()
        if move_notation_history:
            move_notation_history.pop()
        board = board_history.pop()
        current_turn *= -1
        last_move = move_history[-1] if move_history else None


def reset_game():
    global board, current_turn, selected_square, move_count, running
    global game_over, en_passant_target, captured_pieces, has_moved
    global board_history, move_history, piece_history, move_notation_history, last_move

    import engine_w

    board = copy.deepcopy(initial_board)
    current_turn = 1
    selected_square = None
    move_count = 0
    game_over = False
    en_passant_target = None
    captured_pieces = {'white': [], 'black': []}
    has_moved = set()
    board_history = []
    move_history = []
    piece_history = []
    move_notation_history = []
    last_move = None
    engine_w.reset_search_state_w()


def make_move(start_row, start_col, end_row, end_col):
    global current_turn, en_passant_target, last_move

    import moves_w
    import notation_w

    if moves_w.is_legal_move(board, start_row, start_col, end_row, end_col):

        board_before_move = copy.deepcopy(board)
        board_history.append(board_before_move)
        move_history.append(((start_row, start_col), (end_row, end_col)))
        piece_history.append(board[start_row][start_col])

        piece = board[start_row][start_col]
        color = 'white' if piece > 0 else 'black'

        captured_piece, en_passant_target = moves_w.apply_special_moves(
            board, start_row, start_col, end_row, end_col
        )

        move_notation = notation_w.move_to_notation(
            board_before_move,
            piece,
            start_row,
            start_col,
            end_row,
            end_col,
            captured_piece
        )
        if moves_w.is_in_check(board, 'black' if piece > 0 else 'white'):
            move_notation += "+"
        move_notation_history.append(move_notation)

        move_number = len(move_history) // 2 + (1 if len(move_history) % 2 else 0)
        move_prefix = f"{move_number}. " if piece > 0 else f"{move_number}... "
        print(f"{move_prefix}{move_notation}")

        if captured_piece != 0:
            captured_pieces[color].append(captured_piece)

        if abs(piece) == 1 and abs(end_col - start_col) == 2:
            has_moved.add(f'{color}_rook_{7 if end_col == 6 else 0}')

        if abs(piece) == 1:
            has_moved.add(f'{color}_king')
        if abs(piece) == 5:
            has_moved.add(f'{color}_rook_{start_col}')

        last_move = ((start_row, start_col), (end_row, end_col))
        current_turn *= -1
