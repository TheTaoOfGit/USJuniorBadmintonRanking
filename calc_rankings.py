#!/usr/bin/env python3
"""
Calculate USA Badminton Junior ranking scores from draw CSVs.
Top 4 highest scores from eligible tournaments count toward total.
US Selection is excluded (selection purposes only).
"""

import csv
import json
import os
import re
from collections import defaultdict

# ── Tournament type mapping ──────────────────────────────────────────────────
# None = excluded from ranking points
TOURNAMENT_TYPES = {
    '2025_Junior_Nationals':   'JN',
    '2025_NE_MassBad_OLC':     'OLC',
    '2025_ABC_OLC':            'OLC',
    '2025_Austin_South_CRC':   'OLC',
    '2025_Schafer_SLG_OLC':    'OLC',
    '2025_Dave_Freeman_OLC':   'OLC',
    '2025_Peak_Sports_OLC':    'OLC',
    '2025_US_Selection':       None,    # selection only — no ranking points
    '2025_OBA_NW_OLC':         'OLC',
    '2025_SPBA_Midwest_ORC':   'ORC',
    '2025_CanAm_NorCal_OLC':   'OLC',
    '2025_Bellevue_NW_ORC':    'ORC',
    '2025_Austin_South_OLC':   'OLC',
    '2025_LIBC_NE_ORC':        'ORC',
    '2025_Synergy_NorCal_ORC': 'ORC',
    '2025_Egret_Midwest_OLC':  'OLC',
    '2025_Schafer_SLG_OLC2':   'OLC',
    '2025_Fortius_South_CRC':  'OLC',
    '2025_SGVBC_SoCal_CRC':    'OLC',
    '2025_Capital_NE_OLC':     'OLC',
    '2025_Peak_Sports_OLC2':   'OLC',
    '2026_Wayside_NE_CRC':     'OLC',
    '2026_CBA_Midwest_OLC':    'OLC',
    '2026_Arena_SoCal_ORC':    'ORC',
    '2026_DFW_South_ORC':      'ORC',
    '2026_Dave_Freeman_OLC':   'OLC',
    '2026_Seattle_NW_CRC':     'OLC',
    '2026_PlayNThrive_MW_CRC': 'OLC',
    '2026_Bintang_NorCal_OLC': 'OLC',
}

# ── Points table ─────────────────────────────────────────────────────────────
# Each entry: (rank_lo, rank_hi, points)
POINTS_TABLE = {
    'U19': {
        'JN':  [(1,1,20000),(2,2,18000),(3,3,17000),(4,4,16000),(5,5,15000),
                (6,6,13000),(7,8,11000),(9,12,9000),(13,16,7000),(17,24,6000),
                (25,32,4000),(33,48,3000),(49,64,2000),(65,96,1500),(97,128,1000),
                (129,256,500)],
        'ORC': [(1,1,10000),(2,2,9000),(3,3,8500),(4,4,8000),(5,8,6250),
                (9,16,4000),(17,32,2500),(33,64,1000),(65,128,500),(129,256,250)],
        'OLC': [(1,1,3000),(2,2,2700),(3,3,2550),(4,4,2400),(5,8,1875),
                (9,16,1200),(17,32,750),(33,64,300),(65,128,150),(129,256,75)],
    },
    'U17': {
        'JN':  [(1,1,10800),(2,2,9720),(3,3,9180),(4,4,8640),(5,5,8100),
                (6,6,7020),(7,8,5940),(9,12,4860),(13,16,3780),(17,24,3240),
                (25,32,2160),(33,48,1620),(49,64,1080),(65,96,810),(97,128,540),
                (129,256,270)],
        'ORC': [(1,1,5400),(2,2,4860),(3,3,4590),(4,4,4320),(5,8,3375),
                (9,16,2160),(17,32,1350),(33,64,540),(65,128,270),(129,256,135)],
        'OLC': [(1,1,1620),(2,2,1458),(3,3,1377),(4,4,1296),(5,8,1013),
                (9,16,648),(17,32,405),(33,64,162),(65,128,81),(129,256,41)],
    },
    'U15': {
        'JN':  [(1,1,5832),(2,2,5249),(3,3,4957),(4,4,4666),(5,5,4374),
                (6,6,3791),(7,8,3208),(9,12,2624),(13,16,2041),(17,24,1750),
                (25,32,1166),(33,48,875),(49,64,656),(65,96,437),(97,128,291),
                (129,256,146)],
        'ORC': [(1,1,2916),(2,2,2624),(3,3,2479),(4,4,2333),(5,8,1823),
                (9,16,1166),(17,32,729),(33,64,292),(65,128,146),(129,256,73)],
        'OLC': [(1,1,875),(2,2,787),(3,3,744),(4,4,700),(5,8,547),
                (9,16,350),(17,32,219),(33,64,87),(65,128,44),(129,256,22)],
    },
    'U13': {
        'JN':  [(1,1,3149),(2,2,2834),(3,3,2677),(4,4,2519),(5,5,2362),
                (6,6,2047),(7,8,1732),(9,12,1417),(13,16,1102),(17,24,945),
                (25,32,630),(33,48,472),(49,64,354),(65,96,236),(97,128,157),
                (129,256,79)],
        'ORC': [(1,1,1575),(2,2,1417),(3,3,1338),(4,4,1260),(5,8,984),
                (9,16,630),(17,32,394),(33,64,157),(65,128,79),(129,256,39)],
        'OLC': [(1,1,472),(2,2,425),(3,3,402),(4,4,378),(5,8,295),
                (9,16,189),(17,32,118),(33,64,47),(65,128,24),(129,256,12)],
    },
    'U11': {
        'JN':  [(1,1,1701),(2,2,1531),(3,3,1446),(4,4,1360),(5,5,1275),
                (6,6,1105),(7,8,935),(9,12,765),(13,16,595),(17,24,510),
                (25,32,340),(33,48,255),(49,64,191),(65,96,128),(97,128,85),
                (129,256,43)],
        'ORC': [(1,1,850),(2,2,765),(3,3,723),(4,4,680),(5,8,531),
                (9,16,340),(17,32,213),(33,64,85),(65,128,43),(129,256,21)],
        'OLC': [(1,1,255),(2,2,230),(3,3,217),(4,4,204),(5,8,159),
                (9,16,102),(17,32,64),(33,64,26),(65,128,13),(129,256,6)],
    },
}

# ── Load official eligible player lists ──────────────────────────────────────
def _name_key(name):
    """(first_token, last_token) in lowercase — used for eligibility matching."""
    tokens = name.strip().split()
    if len(tokens) < 2:
        return None
    return (tokens[0].lower(), tokens[-1].lower())

with open('data/eligible_players.json', encoding='utf-8') as _f:
    _raw_eligible = json.load(_f)

# eligible_keys[(disc, age)] = set of (first, last) tuples from official site
# eligible_full[(disc, age)] = set of full normalized names
ELIGIBLE_KEYS = {}
ELIGIBLE_FULL = {}
for _key, _players in _raw_eligible.items():
    _disc, _age = _key.split('_')
    _keys = set()
    _full = set()
    for _p in _players:
        _k = _name_key(_p['name'])
        if _k:
            _keys.add(_k)
        _full.add(_p['name'].strip().title())
    ELIGIBLE_KEYS[(_disc, _age)] = _keys
    ELIGIBLE_FULL[(_disc, _age)] = _full

# Players who play down in age but should NOT earn points in that younger group.
# Format: (normalized_name, discipline_or_'*', age_group) — '*' matches any discipline.
INELIGIBLE_OVERRIDES = {
    ('Sophia Liu', '*', 'U13'),  # USAB 399616, actually U15
    ('Sophia Liu', '*', 'U11'),
}

def _is_overridden(player_name, discipline, age_group):
    for name, disc, age in INELIGIBLE_OVERRIDES:
        if name == player_name and age == age_group:
            if disc == '*' or disc == discipline:
                return True
    return False

def is_eligible(player_name, discipline, age_group):
    """Return True if the player appears on the official eligible list."""
    if _is_overridden(player_name, discipline, age_group):
        return False
    full = ELIGIBLE_FULL.get((discipline, age_group), set())
    if player_name in full:
        return True
    key = _name_key(player_name)
    if key is None:
        return False
    return key in ELIGIBLE_KEYS.get((discipline, age_group), set())

def get_points(age_group, tourn_type, rank_lo):
    """Return points for age_group / tournament type / rank_lo."""
    for lo, hi, pts in POINTS_TABLE.get(age_group, {}).get(tourn_type, []):
        if lo <= rank_lo <= hi:
            return pts
    return 0

# ── Normalize player name for grouping ───────────────────────────────────────
_SCORE_PAT = re.compile(r'^\d{1,2}-\d')   # looks like a score e.g. "21-521-10"

def normalize_name(raw):
    """
    Clean and normalize a player name for deduplication.
    - Strip [USA] / [XXX] national-team prefixes
    - Strip trailing empty brackets []
    - Title-case to merge all-caps surnames (e.g. "Grace CHENG" → "Grace Cheng")
    Returns '' if the string doesn't look like a real name.
    """
    s = raw.strip()
    # Drop national prefixes like [USA], [CHN] …
    s = re.sub(r'^\[.*?\]\s*', '', s)
    # Drop empty or lone brackets at end
    s = re.sub(r'\s*\[\s*\]\s*$', '', s).strip()
    # Reject score strings, empty, or single-token all-digits
    if not s or _SCORE_PAT.match(s):
        return ''
    # Title-case to unify "Grace CHENG" with "Grace Cheng"
    return s.title()

# ── Split doubles player string into individual names ─────────────────────────
def split_doubles_players(player_str, discipline):
    """
    For doubles (BD/GD/XD), the player field contains both partners concatenated.
    Formats seen:
      - "PlayerA [seed]PlayerB"  → split on seed bracket
      - "PlayerAPlayerB"         → split at first lowercase→uppercase boundary
    Returns list of individual names.
    """
    if discipline not in ('BD', 'GD', 'XD'):
        return [player_str]

    s = player_str.strip()

    # Case 1: seed bracket present → split on bracket
    parts = re.split(r'\s*\[.*?\]\s*', s)
    parts = [p.strip() for p in parts if p.strip()]
    if len(parts) == 2:
        return parts

    # Case 2: concatenated without separator → split at first lowercase→uppercase boundary
    # e.g. "Grace ChengZelenia Shen" → "Grace Cheng" + "Zelenia Shen"
    m = re.search(r'(?<=[a-z])(?=[A-Z])', s)
    if m:
        p1, p2 = s[:m.start()].strip(), s[m.start():].strip()
        if p1 and p2:
            return [p1, p2]

    return [s]  # fallback: treat as single entry

# ── Parse event string → (discipline, age_group) ─────────────────────────────
def parse_event(event_str):
    s = event_str.strip()
    m = re.match(r'^(BS|GS|BD|GD|XD)\s+(U\d+)$', s, re.I)
    if m:
        return m.group(1).upper(), m.group(2).upper()
    m = re.match(r'^(U\d+)\s+(BS|GS|BD|GD|XD)$', s, re.I)
    if m:
        return m.group(2).upper(), m.group(1).upper()
    return None, None

# ── Load all draw CSVs ────────────────────────────────────────────────────────
DRAWS_DIR = 'data/draws'
all_results = []

for fname in sorted(os.listdir(DRAWS_DIR)):
    if not fname.endswith('.csv'):
        continue
    key = fname[:-4]
    tourn_type = TOURNAMENT_TYPES.get(key)
    if tourn_type is None:
        continue  # skip excluded tournaments

    with open(os.path.join(DRAWS_DIR, fname), encoding='utf-8') as f:
        for row in csv.DictReader(f):
            disc, age = parse_event(row['event'])
            if not disc or not age:
                continue
            rank_lo = int(row['rank_lo'])
            pts = get_points(age, tourn_type, rank_lo)
            all_results.append({
                'key':        key,
                'tourn_type': tourn_type,
                'tournament': row['tournament'],
                'dates':      row['dates'],
                'event':      row['event'],
                'discipline': disc,
                'age_group':  age,
                'player':     row['player'],
                'rank_lo':    rank_lo,
                'rank_hi':    int(row['rank_hi']),
                'elim_round': row['elim_round'],
                'points':     pts,
            })

# ── Determine each player's floor age group from the official eligible list ───
# A player's lowest listed age group is their floor — no points below it.
# They CAN earn points in higher age groups if they played up in an official tournament.
AGE_LEVELS = {'U11': 0, 'U13': 1, 'U15': 2, 'U17': 3, 'U19': 4}
AGE_BY_LEVEL = {v: k for k, v in AGE_LEVELS.items()}

# player_floor_age[(name, discipline)] = lowest age level from official eligible list
player_floor_age = {}
for (disc, age), names in ELIGIBLE_FULL.items():
    level = AGE_LEVELS.get(age)
    if level is None:
        continue
    for full_name in names:
        key = (full_name, disc)
        if key not in player_floor_age or level < player_floor_age[key]:
            player_floor_age[key] = level
# Also check by first/last key for players whose names don't exactly match
player_floor_age_by_key = {}
for (disc, age), keys in ELIGIBLE_KEYS.items():
    level = AGE_LEVELS.get(age)
    if level is None:
        continue
    for nk in keys:
        key = (nk, disc)
        if key not in player_floor_age_by_key or level < player_floor_age_by_key[key]:
            player_floor_age_by_key[key] = level

def get_floor_level(player_name, discipline):
    """Return the lowest age level this player is listed for (from official list)."""
    fl = player_floor_age.get((player_name, discipline))
    if fl is not None:
        return fl
    nk = _name_key(player_name)
    if nk:
        fl = player_floor_age_by_key.get((nk, discipline))
        if fl is not None:
            return fl
    return None  # not on any official list

# ── Build "played-in" set: players who actually competed in a discipline+age ──
played_in = set()  # (normalized_name, discipline, age_group)
for r in all_results:
    individuals = split_doubles_players(r['player'], r['discipline'])
    for raw_name in individuals:
        name = normalize_name(raw_name)
        if name:
            played_in.add((name, r['discipline'], r['age_group']))

def is_eligible_extended(player_name, discipline, age_group):
    """
    Eligible if:
      1. On the official list for this discipline+age, OR
      2. Has played up into this age group at an official tournament
         AND this age group is >= their floor age group from the official list.
    Never eligible below their floor age group.
    """
    if _is_overridden(player_name, discipline, age_group):
        return False
    target_level = AGE_LEVELS.get(age_group)
    if target_level is None:
        return False
    floor = get_floor_level(player_name, discipline)
    if floor is not None and target_level < floor:
        return False  # never earn points below floor age group
    if is_eligible(player_name, discipline, age_group):
        return True
    # Allow if they played in this age group AND have a floor (i.e. are on the official list)
    if floor is not None and (player_name, discipline, age_group) in played_in:
        return True
    return False

# ── Group by player + discipline + age_group ─────────────────────────────────
# For doubles, split pair strings into individual player names so each person
# gets their own ranking entry.
player_results = defaultdict(list)
for r in all_results:
    individuals = split_doubles_players(r['player'], r['discipline'])
    for raw_name in individuals:
        name = normalize_name(raw_name)
        if not name:
            continue  # skip score strings and garbage
        # Check eligibility: player results count in their own age group
        # AND carry up to the next older age group (U11→U13, U13→U15, etc.)
        event_age = r['age_group']
        OLDER_AGE = {'U11': 'U13', 'U13': 'U15', 'U15': 'U17', 'U17': 'U19'}
        entry = dict(r, player=name)
        added = False
        # Count in the event's own age group if eligible (official list or played-up)
        if is_eligible_extended(name, r['discipline'], event_age):
            player_results[(name, r['discipline'], event_age)].append(entry)
            added = True
        # Also carry up to the older age group if eligible there
        if event_age in OLDER_AGE and is_eligible_extended(name, r['discipline'], OLDER_AGE[event_age]):
            player_results[(name, r['discipline'], OLDER_AGE[event_age])].append(entry)
            added = True
        if not added:
            continue

# ── Calculate top-4 scores ────────────────────────────────────────────────────
ranking_rows = []
for (player, disc, age), results in player_results.items():
    by_pts = sorted(results, key=lambda x: -x['points'])
    top4   = by_pts[:4]
    total  = sum(r['points'] for r in top4)
    detail = ' | '.join(
        f"{r['key']}(rank {r['rank_lo']}-{r['rank_hi']} = {r['points']} pts)"
        for r in top4
    )
    ranking_rows.append({
        'player':     player,
        'discipline': disc,
        'age_group':  age,
        'total_pts':  total,
        'tournaments_counted': len(top4),
        'tournaments_total':   len(results),
        'top4_detail': detail,
    })

# Sort: age_group, discipline, score descending
AGE_ORDER = ['U11','U13','U15','U17','U19']
DISC_ORDER = ['BS','GS','BD','GD','XD']
ranking_rows.sort(key=lambda x: (
    AGE_ORDER.index(x['age_group']) if x['age_group'] in AGE_ORDER else 99,
    DISC_ORDER.index(x['discipline']) if x['discipline'] in DISC_ORDER else 99,
    -x['total_pts'],
))

# ── Write output ──────────────────────────────────────────────────────────────
out_path = 'data/player_rankings.csv'
fields = ['player','discipline','age_group','total_pts',
          'tournaments_counted','tournaments_total','top4_detail']
with open(out_path, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(ranking_rows)

print(f"Wrote {len(ranking_rows)} entries to {out_path}")

# ── Spot-check: Grace Cheng ───────────────────────────────────────────────────
print("\n--- Grace Cheng ---")
for row in ranking_rows:
    if 'Grace' in row['player'] and 'Cheng' in row['player']:
        print(f"  {row['discipline']} {row['age_group']:4s}  {row['total_pts']:6,} pts  ({row['tournaments_counted']}/{row['tournaments_total']} tournaments)")
        for item in row['top4_detail'].split(' | '):
            print(f"    {item}")
