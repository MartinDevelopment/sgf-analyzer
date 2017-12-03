import hashlib
import os
import re
import sys

import config
from sgftools.sgflib import SGFParser

comment_regex = r"(?P<nickname>[\w\W]+)+: (?P<node_comment>[\w\W]+)+"


def parse_sgf(path_to_sgf):
    """Return parsed Collection from sgf"""
    if not os.path.exists(path_to_sgf):
        raise FileNotFoundError("No such file: %s" % path_to_sgf)

    with open(path_to_sgf, 'r', encoding="utf-8") as sgf_file:
        data = "".join([line for line in sgf_file])

    return SGFParser(data).parse()


def prepare_checkpoint_dir(sgf):
    """Create unique checkpoint directory"""
    if not os.path.exists(config.checkpoint_dir):
        os.mkdir(config.checkpoint_dir)

    # Get unique hash based on content
    base_hash = hashlib.md5(str(sgf).encode()).hexdigest()
    base_dir = os.path.join(config.checkpoint_dir, base_hash)

    if not os.path.exists(base_dir):
        os.mkdir(base_dir)

    return base_dir


def get_initial_values(cursor):
    node_boardsize = cursor.node.get('SZ')
    if node_boardsize:
        board_size = int(node_boardsize.data[0])
    else:
        board_size = 19

    node_handicap = cursor.node.get('HA')
    if node_handicap and int(node_handicap.data[0]) > 1:
        handicap_stone_count = int(node_handicap.data[0])
    else:
        handicap_stone_count = 0

    node_rules = cursor.node.get('RU')
    is_japanese_rules = node_rules and node_rules.data[0].lower() in ['jp', 'japanese', 'japan']

    node_komi = cursor.node.get('KM')
    if node_komi:
        komi = float(node_komi.data[0])

        if handicap_stone_count and is_japanese_rules:
            old_komi = komi
            komi = old_komi + handicap_stone_count
            print(
                f"Adjusting komi from {old_komi:.1f} to {komi:.1f} in converting to "
                f"Chinese rules with {handicap_stone_count:d} handicap", file=sys.stderr)
    else:
        if handicap_stone_count:
            komi = 0.5
        else:
            komi = 6.5 if is_japanese_rules else 7.5
        print(f"WARNING: Komi not specified, assuming {komi:.1f}", file=sys.stderr)

    game_settings = {
        'board_size': board_size,
        'is_handicap_game': bool(handicap_stone_count),
        'komi': komi
    }

    return game_settings


def collect_requested_moves(cursor, args):
    comment_requests_analyze = {}
    comment_requests_variations = {}
    analyze_tasks_initial = 0
    variations_tasks_initial = 0
    move_num = -1

    while not cursor.atEnd:

        # Go to next node and increment move_num
        cursor.next()
        move_num += 1

        node_comment = cursor.node.get('C')

        # Store moves, requested for analysis and variations
        if node_comment:
            match = re.match(comment_regex, node_comment.data[0])

            if 'analyze' in match.group('node_comment'):
                comment_requests_analyze[move_num] = True

            if 'variations' in match.group('node_comment'):
                comment_requests_analyze[move_num] = True
                comment_requests_variations[move_num] = True

            # Wipe comments is needed
            if args.wipe_comments:
                node_comment.data[0] = ""

        analysis_mode = None

        if args.analyze_start <= move_num <= args.analyze_end:
            analysis_mode = 'analyze'

        if move_num in comment_requests_analyze or (move_num - 1) in comment_requests_analyze or (
                move_num - 1) in comment_requests_variations:
            analysis_mode = 'analyze'

        if move_num in comment_requests_variations:
            analysis_mode = 'variations'

        if analysis_mode == 'analyze':
            analyze_tasks_initial += 1
        elif analysis_mode == 'variations':
            analyze_tasks_initial += 1
            variations_tasks_initial += 1

    return comment_requests_analyze, comment_requests_variations, analyze_tasks_initial, variations_tasks_initial
