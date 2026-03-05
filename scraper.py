"""
Scrape final rankings from all 16 USA Badminton Junior tournaments (2025-2026 season).
Outputs:
  - data/rankings.csv  : one row per player-event-rank
  - data/matches.csv   : one row per match (from draw pages)
  - data/tournaments.json : metadata
"""
import requests
from bs4 import BeautifulSoup
import csv
import json
import re
import time
import os

BASE = "https://www.tournamentsoftware.com"
OUT_DIR = "data"
os.makedirs(OUT_DIR, exist_ok=True)

TOURNAMENTS = [
    {"name": "2025 YONEX Bellevue Northwest ORC",      "id": "D96AD8D0-A9D8-4679-939E-82E9963A49A7", "date_start": "2025-08-30", "date_end": "2025-09-01",  "region": "NW",     "type": "ORC"},
    {"name": "2025 Austin Leander South OLC",           "id": "376A120B-F979-495B-9799-ED548D9A1E7E", "date_start": "2025-09-20", "date_end": "2025-09-21",  "region": "South",  "type": "OLC"},
    {"name": "2025 YONEX LIBC Northeast ORC",           "id": "40CE63A2-430A-4C56-80C7-2DBD701A9019", "date_start": "2025-10-11", "date_end": "2025-10-13",  "region": "NE",     "type": "ORC"},
    {"name": "2025 YONEX Synergy NorCal ORC",           "id": "A3D197AE-C74C-41BF-9C66-F91B7576B77A", "date_start": "2025-11-08", "date_end": "2025-11-10",  "region": "NorCal", "type": "ORC"},
    {"name": "2025 Egret Midwest OLC",                  "id": "F1D5FE50-3A8A-4C5A-8A55-71BE130B6EC3", "date_start": "2025-11-22", "date_end": "2025-11-23",  "region": "MW",     "type": "OLC"},
    {"name": "2025 Schafer SLG South OLC",              "id": "75548892-B29A-420B-9951-973C8C9F2D68", "date_start": "2025-11-29", "date_end": "2025-11-30",  "region": "South",  "type": "OLC"},
    {"name": "2025 Fortius South CRC",                  "id": "22C92233-478E-4239-BCF3-A3A9A054BA2C", "date_start": "2025-12-05", "date_end": "2025-12-07",  "region": "South",  "type": "CRC"},
    {"name": "2025 SGVBC SoCal CRC",                    "id": "FEAC4C02-C295-4225-AA82-CFCBA83B2834", "date_start": "2025-12-06", "date_end": "2025-12-07",  "region": "SoCal",  "type": "CRC"},
    {"name": "2025 Capital NE OLC",                     "id": "86C3EAAF-BA94-42DB-9110-7CD31A5810FD", "date_start": "2025-12-12", "date_end": "2025-12-14",  "region": "NE",     "type": "OLC"},
    {"name": "2025 Peak Sports South OLC",              "id": "66D14DB5-408F-4C65-8400-9E916F6FA5DD", "date_start": "2025-12-20", "date_end": "2025-12-21",  "region": "South",  "type": "OLC"},
    {"name": "2026 Wayside NE CRC",                     "id": "937ACE29-5F1C-4E39-B3FC-DE5DC9F67A6E", "date_start": "2026-01-03", "date_end": "2026-01-04",  "region": "NE",     "type": "CRC"},
    {"name": "2026 CBA Midwest OLC",                    "id": "58FD9D91-2FE9-4613-9E59-6D56ADE8BF5B", "date_start": "2026-01-10", "date_end": "2026-01-11",  "region": "MW",     "type": "OLC"},
    {"name": "2026 YONEX Arena SoCal ORC",              "id": "239635E4-C300-4F6A-A364-7062F0430F30", "date_start": "2026-01-17", "date_end": "2026-01-19",  "region": "SoCal",  "type": "ORC"},
    {"name": "2026 YONEX DFW Badminton South ORC",      "id": "4C4A21C2-E62B-4448-8B0D-12AEE6263B99", "date_start": "2026-02-14", "date_end": "2026-02-16",  "region": "South",  "type": "ORC"},
    {"name": "2026 Dave Freeman Jr. SoCal OLC",         "id": "45D5792F-78E5-43B1-8D72-898357052913", "date_start": "2026-02-20", "date_end": "2026-02-22",  "region": "SoCal",  "type": "OLC"},
    {"name": "2026 Seattle NW CRC",                     "id": "EF556B64-3B34-438D-853D-8812143EC357", "date_start": "2026-02-21", "date_end": "2026-02-22",  "region": "NW",     "type": "CRC"},
]

# ── Helpers ───────────────────────────────────────────────────────────────────

def make_session():
    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/121.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    })
    return s

def accept_cookies(session, tid):
    session.get(f"{BASE}/cookiewall/?returnurl=%2Ftournament%2F{tid}")
    r = session.post(f"{BASE}/cookiewall/Save", data={
        "ReturnUrl": f"/tournament/{tid}",
        "SettingsOpen": "false",
        "CookiePurposes": ["1", "2", "4", "16"],
    })
    return r

def get_with_cookie_retry(session, url, tid, max_retries=2):
    for attempt in range(max_retries + 1):
        r = session.get(url, timeout=20)
        if "cookiewall" in r.url:
            accept_cookies(session, tid)
            continue
        return r
    return None

def parse_seed(name_with_seed):
    """Extract seed from 'Player Name [2]' -> ('Player Name', '2')"""
    m = re.search(r'\[([^\]]+)\]$', name_with_seed.strip())
    if m:
        seed = m.group(1)
        name = name_with_seed[:m.start()].strip()
        return name, seed
    return name_with_seed.strip(), ""

def parse_doubles_entry(raw):
    """
    Split 'Player1 [seed]Player2' or 'Player1Player2 [seed]' into two names.
    Strategy: split at ']' if it appears mid-string, else split at uppercase after lowercase.
    """
    # Case: "Player1 [seed]Player2"
    m = re.search(r'\[[^\]]+\](?=[A-Z])', raw)
    if m:
        p1_raw = raw[:m.end()].strip()
        p2_raw = raw[m.end():].strip()
        name1, seed1 = parse_seed(p1_raw)
        name2, seed2 = parse_seed(p2_raw)
        seed = seed1 or seed2
        return name1, name2, seed
    # Case: both names, seed at end
    p1, seed = parse_seed(raw)
    # Try to find where second player name starts (uppercase after lowercase/space)
    parts = re.split(r'(?<=[a-z]) (?=[A-Z])', p1, maxsplit=1)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip(), seed
    return raw.strip(), "", seed

# ── Parse winners page ────────────────────────────────────────────────────────

def parse_winners_page(html, tournament_meta):
    """
    Returns list of dicts with keys:
      tournament_name, tournament_id, date_start, date_end, region, type,
      event, age_group, discipline, rank, player1, player2, seed
    """
    soup = BeautifulSoup(html, "lxml")
    rows_out = []

    # Each table covers one discipline type (BS, GS, XD, BD, GD)
    tables = soup.find_all("table")
    for tbl in tables:
        rows = tbl.find_all("tr")
        current_event = None
        for row in rows:
            cells = [td.get_text(strip=True) for td in row.find_all(["td", "th"])]
            if not cells:
                continue
            # Event header row: single cell with event name like 'BS U11'
            if len(cells) == 1 and re.match(r'^(BS|GS|XD|BD|GD)\s+U\d+$', cells[0]):
                current_event = cells[0]
                continue
            # Rank row: ['rank', 'name'] or ['rank', 'name1name2'] for doubles
            if len(cells) == 2 and cells[0].isdigit() and current_event:
                rank = int(cells[0])
                raw_name = cells[1]
                # Parse event parts
                m = re.match(r'^(BS|GS|XD|BD|GD)\s+(U\d+)$', current_event)
                if not m:
                    continue
                discipline, age_group = m.group(1), m.group(2)
                is_doubles = discipline in ("XD", "BD", "GD")

                if is_doubles:
                    p1, p2, seed = parse_doubles_entry(raw_name)
                    rows_out.append({
                        **tournament_meta,
                        "event": current_event,
                        "age_group": age_group,
                        "discipline": discipline,
                        "rank": rank,
                        "player1": p1,
                        "player2": p2,
                        "seed": seed,
                    })
                else:
                    p1, seed = parse_seed(raw_name)
                    rows_out.append({
                        **tournament_meta,
                        "event": current_event,
                        "age_group": age_group,
                        "discipline": discipline,
                        "rank": rank,
                        "player1": p1,
                        "player2": "",
                        "seed": seed,
                    })
    return rows_out

# ── Parse draw page for full match results ────────────────────────────────────

def parse_draw_page(html, tournament_meta, event_name, draw_num):
    """
    Parse a draw (bracket) page for individual match results.
    Returns list of match dicts.
    """
    soup = BeautifulSoup(html, "lxml")
    matches = []
    tables = soup.find_all("table")
    if not tables:
        return matches

    # First table is the main bracket
    tbl = tables[0]
    headers = [th.get_text(strip=True) for th in tbl.find("tr").find_all(["th", "td"])]
    # Typical headers: ['', 'Club', 'Round 1', 'Round 2', ..., 'Finals', 'Winner']
    round_names = [h for h in headers if h not in ("", "Club")]

    rows = tbl.find_all("tr")[1:]  # skip header

    # The bracket is structured in a complex way - each player spans multiple rows
    # We need to find score cells (cells containing scores like '21-15 21-13')
    score_pattern = re.compile(r'\d{1,2}-\d{1,2}')

    current_players = {}  # col_index -> player_name
    for row in rows:
        cells = row.find_all(["td", "th"])
        for ci, cell in enumerate(cells):
            text = cell.get_text(strip=True)
            if score_pattern.search(text):
                # This is a score cell
                # The round is determined by column index
                round_idx = ci - 2  # subtract seed# col and club col
                if 0 <= round_idx < len(round_names):
                    round_name = round_names[round_idx]
                    matches.append({
                        **tournament_meta,
                        "event": event_name,
                        "draw": draw_num,
                        "round": round_name,
                        "score": text,
                    })

    return matches

# ── Get draw list for a tournament ────────────────────────────────────────────

def get_draw_list(session, tid):
    """Returns list of (draw_num, event_name) tuples."""
    r = get_with_cookie_retry(session, f"{BASE}/sport/draws.aspx?id={tid}", tid)
    if not r:
        return []
    soup = BeautifulSoup(r.text, "lxml")
    draws = []
    for a in soup.find_all("a", href=True):
        m = re.search(r'draw\.aspx\?id=.+&draw=(\d+)', a["href"])
        if m:
            draw_num = int(m.group(1))
            event_name = a.get_text(strip=True)
            draws.append((draw_num, event_name))
    return draws

# ── Main scraping loop ────────────────────────────────────────────────────────

all_rankings = []
all_matches = []
tournament_log = []

session = make_session()

# Accept cookies for first tournament to init session
accept_cookies(session, TOURNAMENTS[0]["id"])

for t in TOURNAMENTS:
    tid = t["id"]
    tname = t["name"]
    tmeta = {k: t[k] for k in ("name", "id", "date_start", "date_end", "region", "type")}

    print(f"\n{'='*70}")
    print(f"Scraping: {tname}")
    print(f"  ID: {tid}")

    # ── Winners / Rankings ──────────────────────────────────────────────────
    winners_url = f"{BASE}/sport/winners.aspx?id={tid}"
    r = get_with_cookie_retry(session, winners_url, tid)
    time.sleep(0.8)

    if not r or r.status_code != 200:
        print(f"  ERROR: Could not fetch winners page (status={r.status_code if r else 'N/A'})")
        tournament_log.append({**tmeta, "status": "error_winners"})
        continue

    # Check if it's still on cookie wall
    if "cookiewall" in r.url:
        print(f"  WARNING: Still on cookie wall after retry")
        tournament_log.append({**tmeta, "status": "cookie_wall"})
        continue

    rankings = parse_winners_page(r.text, tmeta)
    print(f"  Winners page: {len(rankings)} ranked entries across events")

    if rankings:
        all_rankings.extend(rankings)
        # Show event summary
        events_found = {}
        for row in rankings:
            ev = row["event"]
            if ev not in events_found:
                events_found[ev] = 0
            events_found[ev] += 1
        for ev, cnt in sorted(events_found.items()):
            print(f"    {ev}: {cnt} ranked players")
    else:
        print(f"  WARNING: No rankings data found (tournament may not have results yet)")

    # ── Draw pages for full match results ──────────────────────────────────
    draws = get_draw_list(session, tid)
    print(f"  Found {len(draws)} draws")
    time.sleep(0.5)

    match_count = 0
    for draw_num, event_name in draws:
        draw_url = f"{BASE}/sport/draw.aspx?id={tid}&draw={draw_num}"
        r_draw = get_with_cookie_retry(session, draw_url, tid)
        time.sleep(0.4)
        if not r_draw or r_draw.status_code != 200:
            print(f"    Draw {draw_num} ({event_name}): fetch error")
            continue
        matches = parse_draw_page(r_draw.text, tmeta, event_name, draw_num)
        all_matches.extend(matches)
        match_count += len(matches)

    print(f"  Matches scraped: {match_count}")
    tournament_log.append({**tmeta, "status": "ok", "rankings_count": len(rankings), "matches_count": match_count})

# ── Save output ───────────────────────────────────────────────────────────────

# Rankings CSV
rankings_path = os.path.join(OUT_DIR, "rankings.csv")
if all_rankings:
    fieldnames = ["name", "id", "date_start", "date_end", "region", "type",
                  "event", "age_group", "discipline", "rank", "player1", "player2", "seed"]
    with open(rankings_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rankings)
    print(f"\nSaved {len(all_rankings)} ranking rows -> {rankings_path}")

# Matches CSV
matches_path = os.path.join(OUT_DIR, "matches.csv")
if all_matches:
    fieldnames_m = ["name", "id", "date_start", "date_end", "region", "type",
                    "event", "draw", "round", "score"]
    with open(matches_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames_m)
        writer.writeheader()
        writer.writerows(all_matches)
    print(f"Saved {len(all_matches)} match rows -> {matches_path}")

# Tournament log JSON
log_path = os.path.join(OUT_DIR, "tournaments.json")
with open(log_path, "w", encoding="utf-8") as f:
    json.dump(tournament_log, f, indent=2)
print(f"Saved tournament log -> {log_path}")

print("\n=== SUMMARY ===")
for t in tournament_log:
    status = t.get("status", "?")
    rc = t.get("rankings_count", 0)
    mc = t.get("matches_count", 0)
    print(f"  {t['name']:<45} {status:<15} rankings={rc:3d} matches={mc:4d}")
