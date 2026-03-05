"""
Scrape full draw rankings for all junior tournaments (last 12 months).
Processes one tournament at a time and saves each to data/draws/{key}.csv.
Skips tournaments already saved (safe to resume after interruption).
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import requests
from bs4 import BeautifulSoup
import re, csv, os, time

BASE = "https://www.tournamentsoftware.com"

# ── Tournament list ────────────────────────────────────────────────────────────
# tid=None means ID not yet found; those entries will be skipped with a warning.
TOURNAMENTS = [
    # ── 2024-2025 season (within last 12 months: >= Feb 27 2025) ──────────────
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

    # ── 2025-2026 season ──────────────────────────────────────────────────────
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

OUT_DIR = "data/draws"
os.makedirs(OUT_DIR, exist_ok=True)

FIELDS = ['tournament','dates','event','player','seed','state','draw_pos','rank_lo','rank_hi','elim_round']

# ── Session ────────────────────────────────────────────────────────────────────
def make_session(tid):
    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/121.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    })
    s.get(f"{BASE}/cookiewall/?returnurl=%2Ftournament%2F{tid}")
    s.post(f"{BASE}/cookiewall/Save", data={
        "ReturnUrl": f"/tournament/{tid}",
        "SettingsOpen": "false",
        "CookiePurposes": ["1", "2", "4", "16"],
    })
    return s

# ── Draw parser (max-column approach from v3) ──────────────────────────────────
def strip_seed(raw):
    raw = re.sub(r',?\s*WDN', '', raw).strip()
    m = re.search(r'\[([^\]]+)\]$', raw)
    if m:
        return raw[:m.start()].strip(), m.group(1)
    return raw, ''

def parse_draw(html, event_name, tournament_name, dates):
    soup = BeautifulSoup(html, "lxml")
    tables = soup.find_all("table")
    if not tables:
        return []

    table = tables[0]
    rows  = table.find_all("tr")
    if not rows:
        return []

    hdr       = [c.get_text(strip=True) for c in rows[0].find_all(["th","td"])]

    # Detect name_col from the header: player name sits in the first column
    # whose header looks like a round (Round N, Finals, Winner, etc.).
    # Columns labeled 'Club', 'State', '' etc. are metadata before the name.
    ROUND_HDR = re.compile(r'round|final|semi|quarter|winner|group|match|pool', re.I)
    name_col = 2  # fallback
    for i, h in enumerate(hdr):
        if i == 0:
            continue
        if h and ROUND_HDR.search(h):
            name_col = i
            break

    rcols      = {i: h for i, h in enumerate(hdr) if i >= name_col and h}
    if not rcols:
        return []
    winner_col = max(rcols.keys())

    # Pass 1: player metadata from draw-position rows
    player_info = {}
    for row in rows[1:]:
        cells = row.find_all(["td","th"])
        vals  = [c.get_text(strip=True) for c in cells]
        while len(vals) < len(hdr):
            vals.append('')
        if not vals[0].isdigit():
            continue
        draw_pos = int(vals[0])
        state    = vals[name_col - 1] if name_col >= 2 and len(vals) > name_col - 1 else ''
        raw_name = vals[name_col]     if len(vals) > name_col else ''
        if not raw_name or raw_name.lower() == 'bye':
            continue
        pname, seed = strip_seed(raw_name)
        if not pname:
            continue
        if pname not in player_info:
            player_info[pname] = {'seed': seed, 'state': state, 'draw_pos': draw_pos}

    # Pass 2: max column per player across all cells
    player_max_col = {n: name_col for n in player_info}
    for row in rows[1:]:
        cells = row.find_all(["td","th"])
        vals  = [c.get_text(strip=True) for c in cells]
        while len(vals) < len(hdr):
            vals.append('')
        for ci, val in enumerate(vals):
            if ci < name_col or not val:
                continue
            pname, _ = strip_seed(val)
            if pname in player_max_col and ci > player_max_col[pname]:
                player_max_col[pname] = ci

    # 3rd/4th place match: a small table (~ 6 rows) with 2 players from the
    # main draw semi-finals.  The player who appears in the last column wins
    # (rank 3); the other gets rank 4.
    third_place_winner = None
    for extra_table in tables[1:]:
        erows = extra_table.find_all("tr")
        if not (4 <= len(erows) <= 8):
            continue
        # Collect player names and find who reaches the last column
        tbl_players = []
        tbl_winner  = None
        ncols = max(len(row.find_all(["td","th"])) for row in erows)
        for row in erows[1:]:
            vals = [c.get_text(strip=True) for c in row.find_all(["td","th"])]
            # Row with draw position number → find player name in any cell
            if vals and vals[0].isdigit():
                for v in vals[1:]:
                    if not v:
                        continue
                    pname, _ = strip_seed(v)
                    if pname and pname in player_info:
                        tbl_players.append(pname)
                        break
            # Check the last column for the winner (player name, not score)
            if len(vals) >= ncols:
                v = vals[-1]
                if v:
                    pname, _ = strip_seed(v)
                    if pname and pname in player_info:
                        tbl_winner = pname
        if len(tbl_players) == 2 and tbl_winner and tbl_winner in tbl_players:
            third_place_winner = tbl_winner
            break
        # Bye/walkover: only 1 player found → they get 3rd
        if len(tbl_players) == 1:
            third_place_winner = tbl_players[0]
            break

    # Consolation bracket (JN full-seeding style): look for a table whose
    # first header cell is a round label (no leading draw-pos/State columns).
    # Data rows have an extra leading section# cell so data-col = header-col + 1.
    cons_max_col    = {}   # player -> max data-col in consolation table
    cons_min_col    = {}   # player -> min data-col (entry point)
    cons_winner_col = None
    crcols          = {}   # data-col -> round label (using header-col + 1 offset)

    for extra_table in tables[1:]:
        erows = extra_table.find_all("tr")
        if len(erows) < 20:
            continue
        ehdr = [c.get_text(strip=True) for c in erows[0].find_all(["th","td"])]
        if not ehdr or not ROUND_HDR.search(ehdr[0]):
            continue
        # Build label map: data-col index -> round label
        local_crcols = {i + 1: h for i, h in enumerate(ehdr) if h}
        # Scan all data rows for known player names
        cmax = {}
        cmin = {}
        for row in erows[1:]:
            vals = [c.get_text(strip=True) for c in row.find_all(["td","th"])]
            for ci, val in enumerate(vals):
                if not val:
                    continue
                pname, _ = strip_seed(val)
                if pname in player_info:
                    if pname not in cmax or ci > cmax[pname]:
                        cmax[pname] = ci
                    if pname not in cmin or ci < cmin[pname]:
                        cmin[pname] = ci
        if cmax:
            cons_max_col    = cmax
            cons_min_col    = cmin
            cons_winner_col = max(cmax.values())
            crcols          = local_crcols
            break  # use first matching consolation table

    # Build mapping: main-draw rfe -> consolation entry column
    # (for assigning ranks to players not found in consolation)
    cons_entry_by_rfe = {}
    if cons_winner_col is not None:
        from collections import defaultdict
        rfe_entries = defaultdict(list)
        for pname in cons_min_col:
            main_rfe = winner_col - player_max_col[pname]
            rfe_entries[main_rfe].append(cons_min_col[pname])
        for rfe, cols in rfe_entries.items():
            cons_entry_by_rfe[rfe] = min(cols)  # use earliest entry col

    # Rank assignment
    results = []
    for pname, info in player_info.items():
        mc  = player_max_col[pname]
        rfe = winner_col - mc

        if rfe == 0:
            rank_lo, rank_hi = 1, 1
            elim_round = 'Winner'
        elif rfe == 1:
            rank_lo, rank_hi = 2, 2
            elim_round = rcols.get(mc, f'col{mc}')
        elif rfe == 2 and third_place_winner is not None:
            # 3rd/4th place match exists — split rank 3 vs 4
            if pname == third_place_winner:
                rank_lo, rank_hi = 3, 3
            else:
                rank_lo, rank_hi = 4, 4
            elim_round = rcols.get(mc, f'col{mc}')
        else:
            rank_lo    = 2 ** (rfe - 1) + 1
            rank_hi    = 2 ** rfe
            elim_round = rcols.get(mc, f'col{mc}')

        # Override with consolation rank if consolation bracket exists
        # Double-elimination: band sizes from winner are 1,1,2,4,4,8,8,16,16,...
        # i.e. band_size = 2^((c_rfe+1)//2) for c_rfe >= 2
        def _cons_rank(c_rfe):
            if c_rfe == 0: return 5, 5
            if c_rfe == 1: return 6, 6
            c_lo = 7
            for r in range(2, c_rfe):
                c_lo += 2 ** ((r + 1) // 2)
            band = 2 ** ((c_rfe + 1) // 2)
            return c_lo, c_lo + band - 1

        if cons_winner_col is not None and rfe >= 2:
            if pname in cons_max_col:
                # Player found in consolation — use their exit column
                cmc   = cons_max_col[pname]
                c_rfe = cons_winner_col - cmc
                c_lo, c_hi = _cons_rank(c_rfe)
                c_label = crcols.get(cmc, f'Cons col{cmc}')
                rank_lo    = c_lo
                rank_hi    = c_hi
                elim_round = f'C:{c_label}'
            elif rfe in cons_entry_by_rfe:
                # Player not in consolation (withdrew) — rank as if they
                # lost at their consolation entry point
                entry_col = cons_entry_by_rfe[rfe]
                c_rfe = cons_winner_col - entry_col
                c_lo, c_hi = _cons_rank(c_rfe)
                c_label = crcols.get(entry_col, f'Cons col{entry_col}')
                rank_lo    = c_lo
                rank_hi    = c_hi
                elim_round = f'C:{c_label} (W/O)'

        results.append({
            'tournament': tournament_name,
            'dates':      dates,
            'event':      event_name,
            'player':     pname,
            'seed':       info['seed'],
            'state':      info['state'],
            'draw_pos':   info['draw_pos'],
            'rank_lo':    rank_lo,
            'rank_hi':    rank_hi,
            'elim_round': elim_round,
        })

    return sorted(results, key=lambda x: (x['rank_lo'], x['draw_pos']))

# ── Main loop ──────────────────────────────────────────────────────────────────
skipped_no_tid  = []
skipped_done    = []
processed       = []
failed          = []

for t in TOURNAMENTS:
    key   = t["key"]
    name  = t["name"]
    dates = t["dates"]
    tid   = t["tid"]
    out   = f"{OUT_DIR}/{key}.csv"

    print(f"\n{'='*70}")
    print(f"Tournament: {name}  ({dates})")

    if tid is None:
        print(f"  SKIP — tournament ID not yet known")
        skipped_no_tid.append(name)
        continue

    if os.path.exists(out):
        import csv as _csv
        with open(out, encoding='utf-8') as f:
            n = sum(1 for _ in f) - 1  # subtract header
        print(f"  SKIP — already saved ({n} rows in {out})")
        skipped_done.append(name)
        continue

    try:
        session = make_session(tid)

        r = session.get(f"{BASE}/sport/draws.aspx?id={tid}", timeout=20)
        soup2 = BeautifulSoup(r.text, "lxml")
        draws = []
        for a in soup2.find_all("a", href=True):
            m = re.search(r'draw\.aspx\?id=.+&draw=(\d+)', a["href"])
            if m:
                draws.append((int(m.group(1)), a.get_text(strip=True)))

        if not draws:
            print(f"  WARNING — no draws found")
            failed.append(name)
            continue

        print(f"  Found {len(draws)} draws")
        all_results = []

        for draw_num, event_name in draws:
            r2 = session.get(f"{BASE}/sport/draw.aspx?id={tid}&draw={draw_num}", timeout=20)
            time.sleep(0.3)
            results = parse_draw(r2.text, event_name, name, dates)
            all_results.extend(results)

            rnk1 = [p['player'] for p in results if p['rank_lo'] == 1]
            print(f"  {event_name:<30} {len(results):>4} players   winner: {', '.join(rnk1) if rnk1 else '?'}")

        # Save
        with open(out, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction='ignore')
            w.writeheader()
            w.writerows(all_results)

        print(f"  Saved {len(all_results)} rows -> {out}")
        processed.append((name, len(all_results)))

    except Exception as e:
        print(f"  ERROR: {e}")
        failed.append(name)

    time.sleep(1)  # polite pause between tournaments

# ── Summary ────────────────────────────────────────────────────────────────────
print(f"\n{'='*70}")
print(f"DONE")
print(f"  Processed:      {len(processed)}")
print(f"  Already done:   {len(skipped_done)}")
print(f"  No ID yet:      {len(skipped_no_tid)}")
print(f"  Failed:         {len(failed)}")
if skipped_no_tid:
    print(f"\nMissing IDs:")
    for n in skipped_no_tid:
        print(f"  - {n}")
if failed:
    print(f"\nFailed:")
    for n in failed:
        print(f"  - {n}")
