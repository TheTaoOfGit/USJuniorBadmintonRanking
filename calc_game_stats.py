"""
Calculate per-player game-point stats from match_details.csv.
Outputs data/player_game_stats.csv with top 100 players by total points scored.
"""
import csv, re
from collections import defaultdict

def split_doubles(name, event):
    disc = event.split()[0] if event else ''
    if disc not in ('BD', 'GD', 'XD'):
        return [name]
    parts = re.split(r'\s*\[.*?\]\s*', name)
    parts = [p.strip() for p in parts if p.strip()]
    if len(parts) == 2:
        return parts
    m = re.search(r'(?<=[a-z])(?=[A-Z])', name)
    if m:
        p1, p2 = name[:m.start()].strip(), name[m.start():].strip()
        if p1 and p2:
            return [p1, p2]
    return [name]

def normalize(name):
    s = re.sub(r'^\[.*?\]\s*', '', name.strip())
    s = re.sub(r'\s*\[\s*\]\s*$', '', s).strip()
    return s.title() if s else ''

JUNK = {'Walkover', 'Bye', 'Retired', 'Wdn', ''}

def parse_games(score_raw):
    games = []
    pos = 0
    while pos < len(score_raw):
        m = re.match(r'(\d{1,2})-', score_raw[pos:])
        if not m:
            pos += 1
            continue
        a = int(m.group(1))
        dpos = pos + m.end()
        rest = score_raw[dpos:]
        if not rest or not rest[0].isdigit():
            pos = dpos
            continue
        if rest[0] == '0':
            b = 0
            pos = dpos + 1
        elif len(rest) >= 2 and rest[1].isdigit() and int(rest[:2]) <= 30:
            two = int(rest[:2])
            after_two = rest[2:]
            after_one = rest[1:]
            if not after_two or re.match(r'\d{1,2}-', after_two):
                b = two
                pos = dpos + 2
            elif not after_one or re.match(r'\d{1,2}-', after_one):
                b = int(rest[0])
                pos = dpos + 1
            else:
                b = two
                pos = dpos + 2
        else:
            b = int(rest[0])
            pos = dpos + 1
        games.append((a, b))
    return games

def new_stats():
    return {
        'pts_scored': 0, 'pts_against': 0,
        'mw': 0, 'ml': 0,
        'games_played': 0, 'games_won': 0, 'games_lost': 0,
        'three_game_matches': 0, 'three_game_wins': 0, 'three_game_losses': 0,
        'straight_wins': 0, 'straight_losses': 0,
        'biggest_win_margin': 0, 'biggest_loss_margin': 0,
        'shutout_games_won': 0, 'shutout_games_lost': 0,
        'tournaments': set(),
    }

stats = defaultdict(new_stats)

with open('data/match_details.csv', encoding='utf-8') as f:
    for row in csv.DictReader(f):
        event = row['event']
        score_raw = row['score']
        tourn = row['tournament']
        games = parse_games(score_raw)
        if not games:
            continue
        n_games = len(games)
        is_three = n_games == 3

        w_games_won = sum(1 for a, b in games if a > b)
        w_games_lost = sum(1 for a, b in games if b > a)
        w_pts = sum(a for a, b in games)
        l_pts = sum(b for a, b in games)
        margin = w_pts - l_pts
        is_straight = (w_games_won == 2 and w_games_lost == 0)
        w_shutouts = sum(1 for a, b in games if a > b and b == 0)

        for p in split_doubles(row['winner'], event):
            name = normalize(p)
            if name in JUNK:
                continue
            s = stats[name]
            s['pts_scored'] += w_pts
            s['pts_against'] += l_pts
            s['mw'] += 1
            s['games_played'] += n_games
            s['games_won'] += w_games_won
            s['games_lost'] += w_games_lost
            s['tournaments'].add(tourn)
            if is_three:
                s['three_game_matches'] += 1
                s['three_game_wins'] += 1
            if is_straight:
                s['straight_wins'] += 1
            if margin > s['biggest_win_margin']:
                s['biggest_win_margin'] = margin
            s['shutout_games_won'] += w_shutouts

        for p in split_doubles(row['loser'], event):
            name = normalize(p)
            if name in JUNK:
                continue
            s = stats[name]
            s['pts_scored'] += l_pts
            s['pts_against'] += w_pts
            s['ml'] += 1
            s['games_played'] += n_games
            s['games_won'] += w_games_lost
            s['games_lost'] += w_games_won
            s['tournaments'].add(tourn)
            if is_three:
                s['three_game_matches'] += 1
                s['three_game_losses'] += 1
            if is_straight:
                s['straight_losses'] += 1
            if margin > s['biggest_loss_margin']:
                s['biggest_loss_margin'] = margin
            s['shutout_games_lost'] += w_shutouts

ranked = sorted(stats.items(), key=lambda x: -x[1]['pts_scored'])[:100]

# Write CSV
fields = [
    'rank', 'player', 'tournaments_played',
    'matches', 'wins', 'losses', 'win_pct',
    'games_played', 'games_won', 'games_lost', 'game_win_pct',
    'pts_scored', 'pts_against', 'pt_diff', 'avg_pts_per_match', 'avg_pts_per_game',
    'three_game_matches', 'three_game_wins', 'three_game_losses', 'three_game_pct',
    'straight_set_wins', 'straight_set_losses',
    'biggest_win_margin', 'biggest_loss_margin',
    'shutout_games_won', 'shutout_games_lost',
]

with open('data/player_game_stats.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    for i, (name, s) in enumerate(ranked, 1):
        tm = s['mw'] + s['ml']
        gp = s['games_played']
        w.writerow({
            'rank': i,
            'player': name,
            'tournaments_played': len(s['tournaments']),
            'matches': tm,
            'wins': s['mw'],
            'losses': s['ml'],
            'win_pct': round(100 * s['mw'] / tm, 1) if tm else 0,
            'games_played': gp,
            'games_won': s['games_won'],
            'games_lost': s['games_lost'],
            'game_win_pct': round(100 * s['games_won'] / gp, 1) if gp else 0,
            'pts_scored': s['pts_scored'],
            'pts_against': s['pts_against'],
            'pt_diff': s['pts_scored'] - s['pts_against'],
            'avg_pts_per_match': round(s['pts_scored'] / tm, 1) if tm else 0,
            'avg_pts_per_game': round(s['pts_scored'] / gp, 1) if gp else 0,
            'three_game_matches': s['three_game_matches'],
            'three_game_wins': s['three_game_wins'],
            'three_game_losses': s['three_game_losses'],
            'three_game_pct': round(100 * s['three_game_matches'] / tm, 1) if tm else 0,
            'straight_set_wins': s['straight_wins'],
            'straight_set_losses': s['straight_losses'],
            'biggest_win_margin': s['biggest_win_margin'],
            'biggest_loss_margin': s['biggest_loss_margin'],
            'shutout_games_won': s['shutout_games_won'],
            'shutout_games_lost': s['shutout_games_lost'],
        })

print(f"Wrote top 100 to data/player_game_stats.csv\n")

# Print compact table
hdr = (f"{'#':>3} {'Player':<28} {'T':>2} {'M':>4} {'W':>3}-{'L':<3} "
       f"{'W%':>5} {'GP':>4} {'GW':>4}-{'GL':<4} {'G%':>5} "
       f"{'Pts':>6} {'Agst':>6} {'Diff':>6} {'P/M':>5} {'P/G':>5} "
       f"{'3GM':>4} {'3GW':>3}-{'3GL':<3} {'3G%':>5} "
       f"{'SSW':>4} {'SSL':>4} {'BWM':>4} {'BLM':>4} {'SOW':>3} {'SOL':>3}")
print(hdr)
print('-' * len(hdr))
for i, (name, s) in enumerate(ranked, 1):
    tm = s['mw'] + s['ml']
    gp = s['games_played']
    print(f"{i:3} {name:<28} {len(s['tournaments']):>2} {tm:>4} {s['mw']:>3}-{s['ml']:<3} "
          f"{100*s['mw']/tm:>5.1f} {gp:>4} {s['games_won']:>4}-{s['games_lost']:<4} {100*s['games_won']/gp:>5.1f} "
          f"{s['pts_scored']:>6} {s['pts_against']:>6} {s['pts_scored']-s['pts_against']:>+6} {s['pts_scored']/tm:>5.1f} {s['pts_scored']/gp:>5.1f} "
          f"{s['three_game_matches']:>4} {s['three_game_wins']:>3}-{s['three_game_losses']:<3} {100*s['three_game_matches']/tm:>5.1f} "
          f"{s['straight_wins']:>4} {s['straight_losses']:>4} {s['biggest_win_margin']:>4} {s['biggest_loss_margin']:>4} {s['shutout_games_won']:>3} {s['shutout_games_lost']:>3}")
