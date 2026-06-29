import moves_w
import state_w


def square_name(row, col):
    file_name = chr(ord("a") + col)
    rank_name = str(8 - row)
    return f"{file_name}{rank_name}"


def piece_to_letter(piece):
    return {
        1: "K",
        2: "Q",
        3: "B",
        4: "N",
        5: "R",
        6: "",
    }[abs(piece)]


def notation_disambiguation(board, piece, start_row, start_col, end_row, end_col):
    piece_type = abs(piece)
    if piece_type in (1, 6):
        return ""

    color_sign = 1 if piece > 0 else -1
    conflicting_moves = []

    for row in range(8):
        for col in range(8):
            if row == start_row and col == start_col:
                continue
            if board[row][col] == color_sign * piece_type:
                if (end_row, end_col) in moves_w.get_legal_moves(board, row, col):
                    conflicting_moves.append((row, col))

    if not conflicting_moves:
        return ""

    need_file = any(row == start_row for row, _ in conflicting_moves)
    need_rank = any(col == start_col for _, col in conflicting_moves)

    if need_file and need_rank:
        return square_name(start_row, start_col)
    if need_file:
        return chr(ord("a") + start_col)
    if need_rank:
        return str(8 - start_row)
    return chr(ord("a") + start_col)


def move_to_notation(board_state_w, piece, start_row, start_col, end_row, end_col, captured_piece):
    piece_type = abs(piece)

    if piece_type == 1 and abs(end_col - start_col) == 2:
        notation = "O-O" if end_col == 6 else "O-O-O"
    else:
        destination = square_name(end_row, end_col)
        is_capture = captured_piece != 0 or (
            piece_type == 6 and start_col != end_col
        )

        if piece_type == 6:
            prefix = chr(ord("a") + start_col) if is_capture else ""
            notation = f"{prefix}x{destination}" if is_capture else destination
        else:
            letter = piece_to_letter(piece)
            disambiguation = notation_disambiguation(board_state_w, piece, start_row, start_col, end_row, end_col)
            notation = f"{letter}{disambiguation}{'x' if is_capture else ''}{destination}"

    if piece_type == 6 and end_row in (0, 7):
        notation += "=Q"

    return notation


def build_move_log_lines():
    lines = []

    for index in range(0, len(state_w.move_notation_history), 2):
        move_number = index // 2 + 1
        white_move = state_w.move_notation_history[index]
        black_move = state_w.move_notation_history[index + 1] if index + 1 < len(state_w.move_notation_history) else None

        if black_move is None:
            lines.append(f"{move_number}. {white_move}")
        else:
            lines.append(f"{move_number}. {white_move} {black_move}")

    return lines
