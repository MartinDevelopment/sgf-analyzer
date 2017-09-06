from sgftools import sgflib


def insert_sequence(cursor, seq, data=None, callback=None):
    if data is None:
        data = [0] * len(seq)
    for (color, mv), elem in zip(seq, data):
        n_node = sgflib.Node()
        assert color in ['white', 'black']
        if color == 'white':
            color = 'W'
        else:
            color = 'B'
        n_node.add_property(sgflib.Property(n_node, color, [mv]))
        cursor.append_node(n_node)
        cursor.next(len(cursor.children) - 1)

        if callback is not None:
            if type(elem) in [list, tuple]:
                elem = list(elem)
            else:
                elem = [elem]
            callback(*tuple([cursor] + elem))

    for i in range(len(seq)):
        cursor.previous()


def format_variation(cursor, seq):
    mv_seq = [(color, mv) for color, mv, _stats, _mv_list in seq]
    mv_data = [('black' if color == 'white' else 'white', stats, mv_list) for color, _mv, stats, mv_list in seq]
    insert_sequence(cursor, mv_seq, mv_data, format_analysis)


def pos_is_pass(pos):
    if pos == "" or pos == "tt":
        return True
    return False


def format_pos(pos, board_size):
    # In an sgf file, passes are the empty string or tt
    if pos_is_pass(pos):
        return "pass"
    if len(pos) != 2:
        return pos
    return "ABCDEFGHJKLMNOPQRSTUVXYZ"[ord(pos[0]) - ord('a')] + str(board_size - (ord(pos[1]) - ord('a')))


def format_winrate(stats, move_list, board_size, next_game_move):
    comment = ""
    if 'winrate' in stats:
        comment += "Overall black win%%: %.2f%%\n" % (stats['winrate'] * 100)
    else:
        comment += "Overall black win%: not computed (Leela still in opening book)\n"

    if len(move_list) > 0 and move_list[0]['pos'] != next_game_move:
        comment += "Leela's preferred next move: %s\n" % format_pos(move_list[0]['pos'], board_size)
    else:
        comment += "\n"

    return comment


def format_delta_info(delta, transdelta, stats, this_move, board_size):
    comment = ""
    lb_values = []
    if transdelta <= -0.200:
        comment += "==========================\n"
        comment += "Big Mistake? (%s) (delta %.2f%%)\n" % (format_pos(this_move, board_size), delta * 100)
        comment += "==========================\n"
        if not pos_is_pass(this_move):
            lb_values.append("%s:%s" % (this_move, "?"))
    elif transdelta <= -0.075:
        comment += "==========================\n"
        comment += "Mistake? (%s) (delta %.2f%%)\n" % (format_pos(this_move, board_size), delta * 100)
        comment += "==========================\n"
        if not pos_is_pass(this_move):
            lb_values.append("%s:%s" % (this_move, "?"))
    elif transdelta <= -0.040:
        comment += "==========================\n"
        comment += "Inaccuracy? (%s) (delta %.2f%%)\n" % (format_pos(this_move, board_size), delta * 100)
        comment += "==========================\n"
        if not pos_is_pass(this_move):
            lb_values.append("%s:%s" % (this_move, "?"))
    elif transdelta <= -0.005:
        comment += "Leela slightly dislikes %s (delta %.2f%%).\n" % (format_pos(this_move, board_size), delta * 100)

    comment += "\n"
    return comment, lb_values


def format_analysis(stats, move_list, this_move):
    abet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    comment = ""
    if 'bookmoves' in stats:
        comment += "==========================\n"
        comment += "Considered %d/%d bookmoves\n" % (stats['bookmoves'], stats['positions'])
    else:
        comment += "==========================\n"
        comment += "Visited %d nodes\n" % (stats['visits'])
        comment += "\n"

        for L, mv in zip(abet, move_list):
            comment += "%s -> Win%%: %.2f%% (%d visits) \n" % (L, mv['winrate'] * 100, mv['visits'])

    # Check for pos being "" or "tt", values which indicate passes, and don't attempt to display markers for them
    lb_values = ["%s:%s" % (mv['pos'], L) for L, mv in zip(abet, move_list) if mv['pos'] != "" and mv['pos'] != "tt"]
    mvs = [mv['pos'] for mv in move_list]
    tr_values = [this_move] if this_move not in mvs and this_move is not None and not pos_is_pass(this_move) else []
    return comment, lb_values, tr_values


def annotate_sgf(cursor, comment, lb_values, tr_values):
    c_node = cursor.node
    if c_node.has_key('C'):
        c_node['C'].data[0] += comment
    else:
        c_node.add_property(c_node.makeProperty('C', [comment]))

    if len(lb_values) > 0:
        c_node.add_property(c_node.makeProperty('LB', lb_values))
    if len(tr_values) > 0:
        c_node.add_property(c_node.makeProperty('TR', tr_values))
