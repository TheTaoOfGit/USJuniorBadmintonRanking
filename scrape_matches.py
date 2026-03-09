"""
Scrape match-level data (player names + scores) from tournamentsoftware.com brackets.
Outputs data/match_details.csv with columns:
  tournament, dates, event, round, winner, loser, score, w_games, l_games
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import requests
from bs4 import BeautifulSoup
import re, csv, os, time

BASE = "https://www.tournamentsoftware.com"

TOURNAMENTS = [
    {"key": "2025_NE_MassBad_OLC",    "name": "2025 NE MassBad OLC",                "dates": "2025-02-28/2025-03-02", "tid": "E6C0A995-9E65-427B-87AB-468A31B36384"},
    {"key": "2025_ABC_OLC",           "name": "2025 ABC NorCal OLC",                "dates": "2025-03-21/2025-03-23", "tid": "4795C1C3-9F40-4DFA-88C6-FC7659DC087D"},
    {"key": "2025_Austin_South_CRC",  "name": "2025 Austin Leander South CRC",      "dates": "2025-03-22/2025-03-23", "tid": "5F149ED1-2D29-4EBF-AE9A-4B3D87D22A2B"},
    {"key": "2025_Schafer_SLG_OLC",   "name": "2025 Schafer SLG South OLC",         "dates": "2025-04-05/2025-04-06", "tid": "487763D5-0AD2-4378-9B51-6E1BD3F84CE5"},
    {"key": "2025_Dave_Freeman_OLC",  "name": "2025 YONEX Dave Freeman Jr. SoCal OLC","dates": "2025-04-12/2025-04-13", "tid": "CF544139-F12A-4B99-A9B9-41E28C9F8266"},
    {"key": "2025_Peak_Sports_OLC",   "name": "2025 Peak Sports South OLC",         "dates": "2025-04-12/2025-04-13", "tid": "66D14DB5-408F-4C65-8400-9E916F6FA5DD"},
    {"key": "2025_US_Selection",      "name": "2025 YONEX U.S. Selection Event",    "dates": "2025-04-18/2025-04-21", "tid": "E5F301F7-ADE5-4AEF-8941-FAD832AEF8F8"},
    {"key": "2025_OBA_NW_OLC",        "name": "2025 OBA NW OLC",                    "dates": "2025-04-26/2025-04-27", "tid": "02D88A67-9666-4648-BE4E-8169AC28A321"},
    {"key": "2025_SPBA_Midwest_ORC",  "name": "2025 YONEX SPBA Midwest ORC",        "dates": "2025-05-24/2025-05-26", "tid": "46A4D2FD-F074-4F11-A86B-34F1ED3E6EC4"},
    {"key": "2025_CanAm_NorCal_OLC",  "name": "2025 CAN-AM Elite NorCal OLC",       "dates": "2025-06-13/2025-06-15", "tid": "56C224B4-0D68-40C6-A8F6-AB16F524C80A"},
    {"key": "2025_Junior_Nationals",  "name": "2025 YONEX U.S. Junior Nationals",   "dates": "2025-07-01/2025-07-07", "tid": "A2DD0F5E-24A4-4875-B053-8F25F31AC357"},
    {"key": "2025_Bellevue_NW_ORC",   "name": "2025 YONEX Bellevue NW ORC",         "dates": "2025-08-30/2025-09-01", "tid": "D96AD8D0-A9D8-4679-939E-82E9963A49A7"},
    {"key": "2025_Austin_South_OLC",  "name": "2025 Austin Leander South OLC",      "dates": "2025-09-20/2025-09-21", "tid": "376A120B-F979-495B-9799-ED548D9A1E7E"},
    {"key": "2025_LIBC_NE_ORC",       "name": "2025 YONEX LIBC NE ORC",             "dates": "2025-10-11/2025-10-13", "tid": "40CE63A2-430A-4C56-80C7-2DBD701A9019"},
    {"key": "2025_Synergy_NorCal_ORC","name": "2025 YONEX Synergy NorCal ORC",      "dates": "2025-11-08/2025-11-10", "tid": "A3D197AE-C74C-41BF-9C66-F91B7576B77A"},
    {"key": "2025_Egret_Midwest_OLC", "name": "2025 Egret Midwest OLC",             "dates": "2025-11-22/2025-11-23", "tid": "F1D5FE50-3A8A-4C5A-8A55-71BE130B6EC3"},
    {"key": "2025_Schafer_SLG_OLC2",  "name": "2025 Schafer SLG South OLC (2025-26)","dates": "2025-11-29/2025-11-30", "tid": "75548892-B29A-420B-9951-973C8C9F2D68"},
    {"key": "2025_Fortius_South_CRC", "name": "2025 Fortius South CRC",             "dates": "2025-12-05/2025-12-07", "tid": "22C92233-478E-4239-BCF3-A3A9A054BA2C"},
    {"key": "2025_SGVBC_SoCal_CRC",   "name": "2025 SGVBC SoCal CRC",               "dates": "2025-12-06/2025-12-07", "tid": "FEAC4C02-C295-4225-AA82-CFCBA83B2834"},
    {"key": "2025_Capital_NE_OLC",    "name": "2025 Capital NE OLC",                "dates": "2025-12-12/2025-12-14", "tid": "86C3EAAF-BA94-42DB-9110-7CD31A5810FD"},
    {"key": "2025_Peak_Sports_OLC2",  "name": "2025 Peak Sports South OLC (Dec)",   "dates": "2025-12-20/2025-12-21", "tid": "78DDAE7C-34D9-4775-81F2-23C18EAC9265"},
    {"key": "2026_Wayside_NE_CRC",    "name": "2026 Wayside NE CRC",                "dates": "2026-01-03/2026-01-04", "tid": "937ACE29-5F1C-4E39-B3FC-DE5DC9F67A6E"},
    {"key": "2026_CBA_Midwest_OLC",   "name": "2026 CBA Midwest OLC",               "dates": "2026-01-10/2026-01-11", "tid": "58FD9D91-2FE9-4613-9E59-6D56ADE8BF5B"},
    {"key": "2026_Arena_SoCal_ORC",   "name": "2026 YONEX Arena SoCal ORC",         "dates": "2026-01-17/2026-01-19", "tid": "239635E4-C300-4F6A-A364-7062F0430F30"},
    {"key": "2026_DFW_South_ORC",     "name": "2026 YONEX DFW South ORC",           "dates": "2026-02-14/2026-02-16", "tid": "4C4A21C2-E62B-4448-8B0D-12AEE6263B99"},
    {"key": "2026_Dave_Freeman_OLC",  "name": "2026 Dave Freeman Jr. SoCal OLC",    "dates": "2026-02-20/2026-02-22", "tid": "45D5792F-78E5-43B1-8D72-898357052913"},
    {"key": "2026_Seattle_NW_CRC",    "name": "2026 Seattle NW CRC",                "dates": "2026-02-21/2026-02-22", "tid": "EF556B64-3B34-438D-853D-8812143EC357"},
]

SCORE_PAT = re.compile(r'(\d{1,2})-(\d{1,2})')

def make_session(tid):
    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/121.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    })
    s.get(f"{BASE}/cookiewall/?returnurl=%2Ftournament%2F{tid}")
    s.post(f"{BASE}/cookiewall/Save", data={
        "ReturnUrl": f"/tournament/{tid}",
        "SettingsOpen": "false",
        "CookiePurposes": ["1", "2", "4", "16"],
    })
    return s

def strip_seed(raw):
    """Remove seed bracket and WDN from player name."""
    raw = re.sub(r',?\s*WDN', '', raw).strip()
    m = re.search(r'\[([^\]]+)\]$', raw)
    if m:
        return raw[:m.start()].strip()
    return raw

def parse_score(raw):
    """
    Parse concatenated score like '21-821-7' or '26-2419-2121-18' into list of (a, b) tuples.
    Scores are concatenated without delimiters. Each game is A-B where A,B in 0..30.
    Returns (games_list, winner_total_points, loser_total_points).
    """
    games = []
    pos = 0
    while pos < len(raw):
        m = re.match(r'(\d{1,2})-', raw[pos:])
        if not m:
            pos += 1
            continue
        a = int(m.group(1))
        dpos = pos + m.end()
        rest = raw[dpos:]
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

    if not games:
        return [], 0, 0
    w_total = sum(g[0] for g in games)
    l_total = sum(g[1] for g in games)
    return games, w_total, l_total

def parse_bracket_matches(html, event_name, tournament_name, dates):
    """
    Parse a bracket page and extract individual matches with player names and scores.

    Pattern: In the bracket table, each column represents a round.
    - Player names appear in column `name_col` (first round column) for seeded entries.
    - As players advance, their names appear in later columns.
    - Scores appear in the same column as the winner's name, but on the adjacent row.

    For a match in round R (column C):
    - Winner's name appears in column C on a "between" row
    - Score appears in column C on the loser's entry row (same column)
    - Both players' names appeared in column C-1 (or name_col for round 1)
    """
    soup = BeautifulSoup(html, "lxml")
    tables = soup.find_all("table")
    if not tables:
        return []

    all_matches = []

    # Process main bracket table and any additional tables (3rd place, consolation)
    for tbl in tables:
        rows = tbl.find_all("tr")
        if len(rows) < 3:
            continue

        hdr = [c.get_text(strip=True) for c in rows[0].find_all(["th", "td"])]

        # Find the name column (first round-like header)
        ROUND_HDR = re.compile(r'round|final|semi|quarter|winner|group|match|pool', re.I)
        name_col = None
        for i, h in enumerate(hdr):
            if i == 0:
                continue
            if h and ROUND_HDR.search(h):
                name_col = i
                break
        if name_col is None:
            continue

        # Build a grid of cell values
        grid = []
        for row in rows[1:]:
            cells = row.find_all(["td", "th"])
            vals = [c.get_text(strip=True) for c in cells]
            while len(vals) < len(hdr):
                vals.append('')
            grid.append(vals)

        # For each column from name_col+1 onward, find matches
        # A match result in column C consists of:
        #   - A row with the winner's name in column C
        #   - A nearby row with the score in column C
        # The two combatants had their names in column C-1

        # First, build a map: for each column, which rows have player names vs scores
        max_col = len(hdr) - 1

        for col in range(name_col + 1, max_col + 1):
            round_name = hdr[col] if col < len(hdr) else f'col{col}'

            # Collect all non-empty entries in this column with their row indices
            entries = []
            for ri, row_vals in enumerate(grid):
                val = row_vals[col] if col < len(row_vals) else ''
                if val:
                    is_score = bool(SCORE_PAT.search(val))
                    entries.append((ri, val, is_score))

            # Group into pairs: each match produces one name entry and one score entry
            # They should be adjacent (within a few rows of each other)
            # Process entries in order - pair each score with the nearest name
            i = 0
            while i < len(entries):
                ri1, val1, is_score1 = entries[i]
                if i + 1 < len(entries):
                    ri2, val2, is_score2 = entries[i + 1]

                    if is_score1 and not is_score2:
                        # Score first, then winner name
                        winner_name = strip_seed(val2)
                        score_raw = val1
                        score_row = ri1
                        i += 2
                    elif not is_score1 and is_score2:
                        # Winner name first, then score
                        winner_name = strip_seed(val1)
                        score_raw = val2
                        score_row = ri2
                        i += 2
                    elif not is_score1 and not is_score2:
                        # Two names without score (bye/walkover) - skip first
                        i += 1
                        continue
                    else:
                        # Two scores? skip first
                        i += 1
                        continue
                else:
                    # Single entry left - could be a walkover winner (no score)
                    i += 1
                    continue

                # Now find the loser: look in column col-1 for the player who isn't the winner
                # The loser's name should be near the score_row in the previous column
                prev_col = col - 1
                loser_name = None

                # Search nearby rows in previous column for a name that isn't the winner
                search_range = max(32, 2 ** (col - name_col))  # bracket spacing grows
                for delta in range(0, search_range):
                    for sign in [0, 1, -1] if delta == 0 else [1, -1]:
                        check_row = score_row + delta * sign
                        if 0 <= check_row < len(grid):
                            prev_val = grid[check_row][prev_col] if prev_col < len(grid[check_row]) else ''
                            if prev_val and not SCORE_PAT.search(prev_val):
                                candidate = strip_seed(prev_val)
                                if candidate and candidate.lower() != 'bye' and candidate != winner_name:
                                    loser_name = candidate
                                    break
                    if loser_name:
                        break

                if not loser_name:
                    continue

                # Parse score
                games, w_pts, l_pts = parse_score(score_raw)
                if not games:
                    continue

                all_matches.append({
                    'tournament': tournament_name,
                    'dates': dates,
                    'event': event_name,
                    'round': round_name,
                    'winner': winner_name,
                    'loser': loser_name,
                    'score': score_raw,
                    'w_points': w_pts,
                    'l_points': l_pts,
                    'num_games': len(games),
                })

    return all_matches

# ── Main ──────────────────────────────────────────────────────────────────────
OUT_PATH = "data/match_details.csv"
FIELDS = ['tournament', 'dates', 'event', 'round', 'winner', 'loser', 'score',
          'w_points', 'l_points', 'num_games']

all_matches = []

for t in TOURNAMENTS:
    key = t["key"]
    tid = t["tid"]
    name = t["name"]
    dates = t["dates"]

    print(f"\n{'='*60}")
    print(f"{name}  ({dates})")

    try:
        session = make_session(tid)

        # Get draw list
        r = session.get(f"{BASE}/sport/draws.aspx?id={tid}", timeout=20)
        soup = BeautifulSoup(r.text, "lxml")
        draws = []
        for a in soup.find_all("a", href=True):
            m = re.search(r'draw\.aspx\?id=.+&draw=(\d+)', a["href"])
            if m:
                draw_num = int(m.group(1))
                event_name = a.get_text(strip=True)
                # Skip group stage sub-draws (e.g. "GS U19 - Group A")
                if ' - Group ' in event_name:
                    continue
                draws.append((draw_num, event_name))

        print(f"  {len(draws)} draws")
        tourn_matches = 0

        for draw_num, event_name in draws:
            url = f"{BASE}/sport/draw.aspx?id={tid}&draw={draw_num}"
            r2 = session.get(url, timeout=20)
            time.sleep(0.3)

            matches = parse_bracket_matches(r2.text, event_name, name, dates)
            all_matches.extend(matches)
            tourn_matches += len(matches)

        print(f"  {tourn_matches} matches extracted")

    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()

    time.sleep(1)

# Write output
with open(OUT_PATH, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=FIELDS)
    w.writeheader()
    w.writerows(all_matches)

print(f"\n{'='*60}")
print(f"Total: {len(all_matches)} matches -> {OUT_PATH}")
