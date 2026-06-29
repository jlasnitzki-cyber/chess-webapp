import copy

import config_w


initial_board = copy.deepcopy(config_w.board_start)
board = copy.deepcopy(initial_board)

board_history = []
state_history = []
move_history = []
piece_history = []
move_notation_history = []

en_passant_target = None
current_turn = 1
player_color = 'white'
selected_square = None
move_count = 0
game_over = False
bot_time_limit_ms = 1000
menu_active = True
running = True

king_moved = False
rook_moved = False
has_moved = set()

captured_pieces = {'white': [], 'black': []}
last_move = None
eval = None


def color_to_sign(color):
    return 1 if color == 'white' else -1


def sign_to_color(sign):
    return 'white' if sign == 1 else 'black'


def engine_color():
    return 'black' if player_color == 'white' else 'white'


def current_turn_color():
    return sign_to_color(current_turn)


def snapshot_state():
    return {
        'current_turn': current_turn,
        'en_passant_target': en_passant_target,
        'captured_pieces': copy.deepcopy(captured_pieces),
        'has_moved': set(has_moved),
        'last_move': last_move,
        'move_count': move_count,
        'game_over': game_over,
    }


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
    global board, current_turn, en_passant_target, captured_pieces, has_moved
    global last_move, move_count, game_over

    if board_history and state_history:
        previous_state = state_history.pop()
        if move_history:
            move_history.pop()
        if piece_history:
            piece_history.pop()
        if move_notation_history:
            move_notation_history.pop()
        board = board_history.pop()
        current_turn = previous_state['current_turn']
        en_passant_target = previous_state['en_passant_target']
        captured_pieces = previous_state['captured_pieces']
        has_moved = previous_state['has_moved']
        last_move = previous_state['last_move']
        move_count = previous_state['move_count']
        game_over = previous_state['game_over']


def reset_game(new_player_color='white'):
    global board, current_turn, selected_square, move_count, running
    global game_over, en_passant_target, captured_pieces, has_moved, player_color
    global board_history, state_history, move_history, piece_history, move_notation_history, last_move

    import engine_w

    board = copy.deepcopy(initial_board)
    current_turn = 1
    player_color = new_player_color
    selected_square = None
    move_count = 0
    game_over = False
    en_passant_target = None
    captured_pieces = {'white': [], 'black': []}
    has_moved = set()
    board_history = []
    state_history = []
    move_history = []
    piece_history = []
    move_notation_history = []
    last_move = None
    engine_w.reset_search_state_w()


def make_move(start_row, start_col, end_row, end_col):
    global current_turn, en_passant_target, last_move, move_count

    import moves_w
    import notation_w

    if moves_w.is_legal_move(board, start_row, start_col, end_row, end_col):

        board_before_move = copy.deepcopy(board)
        board_history.append(board_before_move)
        state_history.append(snapshot_state())
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
        move_count += 1
        current_turn *= -1
