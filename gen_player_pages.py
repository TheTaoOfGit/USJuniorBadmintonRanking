"""Generate player data JSON files + a single player.html template.

Instead of 3,833 individual HTML files, we output:
  - data/players/players_a.json .. players_z.json (+ players_other.json)
  - player.html (single template that loads JSON client-side via ?id=slug)
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import csv, os, re, json
from collections import defaultdict
from html import escape

DRAWS_DIR = "data/draws"
JSON_DIR = "data/players"
os.makedirs(JSON_DIR, exist_ok=True)

# ── Load all results ─────────────────────────────────────────────────────────
def load_all_results():
    """Load all draw CSVs and return dict: player_name -> list of result dicts."""
    all_results = []
    for fn in sorted(os.listdir(DRAWS_DIR)):
        if not fn.endswith('.csv'):
            continue
        with open(os.path.join(DRAWS_DIR, fn), encoding='utf-8') as f:
            for row in csv.DictReader(f):
                if row['player']:
                    all_results.append(row)
    return all_results

def clean_name(raw):
    """Remove seed brackets from name."""
    return re.sub(r'\s*\[[\w/]+\]', '', raw).strip()

def extract_individuals(raw_player, event):
    """Extract individual player names from a player field."""
    clean = clean_name(raw_player)
    if not clean:
        return []
    # Singles
    if any(clean.startswith(p) for p in ['BS ', 'GS ']) or 'Singles' in event:
        return [clean]
    if event.startswith('BS') or event.startswith('GS') or 'Singles' in event:
        return [clean]
    # For doubles, we can't reliably split names without a roster
    # Return the full string - we'll match by substring
    return [clean]

def get_season(date_str):
    year, month = int(date_str[:4]), int(date_str[5:7])
    if month >= 8:
        return f"{year}-{year+1}"
    return f"{year-1}-{year}"

def parse_partner(player_field, player_name):
    clean = clean_name(player_field)
    if clean == player_name:
        return None
    if clean.startswith(player_name):
        return clean[len(player_name):]
    if clean.endswith(player_name):
        return clean[:-len(player_name)]
    return clean.replace(player_name, '').strip() or None

def format_rank(lo, hi):
    lo, hi = int(lo), int(hi)
    return str(lo) if lo == hi else f"{lo}-{hi}"

def slugify(name):
    return re.sub(r'[^a-z0-9]+', '_', name.lower()).strip('_')

# ── Build player index from singles entries ──────────────────────────────────
print("Loading all results...")
all_results = load_all_results()
print(f"  {len(all_results)} total rows")

# First, find all unique player names from singles events
player_names = set()
for r in all_results:
    event = r['event']
    if event.startswith('BS') or event.startswith('GS') or 'Singles' in event:
        name = clean_name(r['player'])
        if name and name.lower() != 'bye':
            player_names.add(name)

# Handle case variations - group by lowercase
name_variants = defaultdict(list)
for n in player_names:
    name_variants[n.lower()].append(n)

# Pick the most common variant
canonical_names = {}
for lower, variants in name_variants.items():
    # Pick the one that appears most in results
    best = max(variants, key=lambda v: sum(1 for r in all_results if v in r['player']))
    for v in variants:
        canonical_names[v] = best

unique_players = set(canonical_names.values())
print(f"  {len(unique_players)} unique players")

# ── Collect results per player ───────────────────────────────────────────────
print("Collecting per-player results...")
player_results = defaultdict(list)
# Build a lookup for fast matching
# For each result, check which players appear in the player field
for r in all_results:
    raw = r['player']
    # Clean raw for matching (remove seeds)
    raw_clean = clean_name(raw)
    for name in unique_players:
        if name in raw_clean:
            player_results[name].append(r)

# ── Generate summary ─────────────────────────────────────────────────────────
def is_singles(event):
    return event.startswith('BS') or event.startswith('GS') or 'Singles' in event

def is_doubles(event):
    return event.startswith('BD') or event.startswith('GD')

def is_mixed(event):
    return event.startswith('XD') or 'Mixed' in event

def disc_label(event):
    if is_singles(event): return 'singles'
    if is_doubles(event): return 'doubles'
    if is_mixed(event): return 'mixed doubles'
    return 'unknown'

def generate_summary(name, results):
    """Generate a comprehensive, dramatic, positive summary based on player stats."""
    if not results:
        return f"<p>{name} is building their tournament journey.</p>"

    first = name.split()[0]
    results_sorted = sorted(results, key=lambda r: r['dates'].split('/')[0])
    seasons = defaultdict(list)
    for r in results_sorted:
        seasons[get_season(r['dates'].split('/')[0])].append(r)

    total_entries = len(results)
    all_tournaments = sorted(set(r['tournament'] for r in results))
    num_tournaments = len(all_tournaments)

    wins = [r for r in results if int(r['rank_lo']) == 1]
    finals = [r for r in results if int(r['rank_lo']) == 2]
    semis = [r for r in results if int(r['rank_lo']) in [3, 4]]
    top8 = [r for r in results if int(r['rank_lo']) <= 8]
    podiums = wins + finals + semis

    # Discipline breakdown
    events_played = set()
    for r in results:
        if is_singles(r['event']): events_played.add('singles')
        if is_doubles(r['event']): events_played.add('doubles')
        if is_mixed(r['event']): events_played.add('mixed')

    s_results = [r for r in results if is_singles(r['event'])]
    d_results = [r for r in results if is_doubles(r['event'])]
    x_results = [r for r in results if is_mixed(r['event'])]
    s_wins = [r for r in wins if is_singles(r['event'])]
    d_wins = [r for r in wins if is_doubles(r['event'])]
    x_wins = [r for r in wins if is_mixed(r['event'])]
    best_singles = min([int(r['rank_lo']) for r in s_results], default=999) if s_results else 999
    best_doubles = min([int(r['rank_lo']) for r in d_results], default=999) if d_results else 999
    best_mixed = min([int(r['rank_lo']) for r in x_results], default=999) if x_results else 999

    # Age groups
    age_groups = set()
    for r in results:
        for ag in ['U11', 'U13', 'U15', 'U17', 'U19']:
            if ag in r['event']:
                age_groups.add(ag)
                break
    ag_sorted = sorted(age_groups, key=lambda x: int(x[1:]))

    # Current age group (most recent)
    current_ag = None
    for r in reversed(results_sorted):
        for ag in ['U11', 'U13', 'U15', 'U17', 'U19']:
            if ag in r['event']:
                current_ag = ag
                break
        if current_ag:
            break

    # Partners analysis
    partners = defaultdict(lambda: {'count': 0, 'wins': 0, 'events': set(), 'best': 999})
    for r in results:
        if is_singles(r['event']): continue
        p = parse_partner(r['player'], name)
        if p:
            partners[p]['count'] += 1
            partners[p]['events'].add(r['event'].split()[0] if ' ' in r['event'] else r['event'][:2])
            rank_lo = int(r['rank_lo'])
            if rank_lo == 1: partners[p]['wins'] += 1
            if rank_lo < partners[p]['best']: partners[p]['best'] = rank_lo
    top_partners = sorted(partners.items(), key=lambda x: -x[1]['count'])
    num_partners = len(partners)

    # Tournament type analysis
    nationals = [r for r in results if 'National' in r['tournament']]
    national_wins = [r for r in nationals if int(r['rank_lo']) == 1]
    national_finals = [r for r in nationals if int(r['rank_lo']) == 2]
    national_podiums = [r for r in nationals if int(r['rank_lo']) <= 4]
    orc_results = [r for r in results if 'ORC' in r['tournament']]
    orc_wins = [r for r in orc_results if int(r['rank_lo']) == 1]
    orc_podiums = [r for r in orc_results if int(r['rank_lo']) <= 4]
    selection = [r for r in results if 'Selection' in r['tournament']]
    selection_podiums = [r for r in selection if int(r['rank_lo']) <= 4]

    # Seeding analysis
    seeded_entries = [r for r in results if r['seed'] and r['seed'] not in ['', 'WC']]
    top_seeds = [r for r in seeded_entries if r['seed'] in ['1', '2']]

    # Trend analysis - compare recent season to earlier
    season_keys = sorted(seasons.keys())
    recent_season = season_keys[-1] if season_keys else None
    recent_results = seasons.get(recent_season, []) if recent_season else []
    recent_wins = [r for r in recent_results if int(r['rank_lo']) == 1]
    recent_podiums = [r for r in recent_results if int(r['rank_lo']) <= 4]

    # Earlier season for comparison
    earlier_season = season_keys[-2] if len(season_keys) >= 2 else None
    earlier_results = seasons.get(earlier_season, []) if earlier_season else []
    earlier_wins = [r for r in earlier_results if int(r['rank_lo']) == 1]

    # Consecutive wins / streaks
    win_events = set()
    for r in wins:
        win_events.add(r['event'])

    # Best tournament (most wins at one tournament)
    tourn_wins = defaultdict(int)
    for r in wins:
        tourn_wins[r['tournament']] += 1
    best_tourn = max(tourn_wins.items(), key=lambda x: x[1]) if tourn_wins else None

    # Regional diversity
    regions = set()
    for t in all_tournaments:
        for region in ['NW', 'NE', 'SoCal', 'NorCal', 'South', 'Midwest']:
            if region in t:
                regions.add(region)
                break

    # ── Build paragraphs ─────────────────────────────────────────────────
    paras = []

    # === OPENING (identity & stature) ===
    if national_wins:
        nat_win_events = list(set(r['event'] for r in national_wins))
        nat_win_str = ", ".join(nat_win_events)
        if len(national_wins) >= 3:
            paras.append(f"{name} is a <strong>multi-event U.S. Junior National Champion</strong> "
                         f"with {len(national_wins)} national titles ({nat_win_str}). "
                         f"In the world of American junior badminton, that puts {first} in truly elite company. "
                         f"Across {total_entries} career entries in {num_tournaments} tournaments, "
                         f"{first} has amassed an extraordinary {len(wins)} tournament victories — "
                         f"a record that speaks to both dominance and durability.")
        else:
            paras.append(f"{name} is a <strong>U.S. Junior National Champion</strong> — "
                         f"a distinction that places {first} among the finest junior players in the country. "
                         f"With {len(wins)} career tournament victories across {num_tournaments} tournaments and "
                         f"{total_entries} total entries, this is a player who consistently rises to the biggest moments.")
    elif len(wins) >= 8:
        paras.append(f"{name} is a <strong>dominant force</strong> in junior badminton with a staggering "
                     f"{len(wins)} tournament titles across {num_tournaments} tournaments. "
                     f"Over {total_entries} career entries, {first} has proven time and again that "
                     f"the biggest stage brings out the best performance. "
                     f"Few players can match this level of sustained excellence.")
    elif len(wins) >= 5:
        paras.append(f"{name} is a <strong>proven champion</strong> with {len(wins)} tournament titles "
                     f"to go along with {len(finals)} Finals and {len(semis)} semifinal appearances across "
                     f"{num_tournaments} tournaments. That kind of consistency at the top "
                     f"doesn't happen by accident — it's the product of relentless preparation and fierce competitive instinct.")
    elif len(wins) >= 2:
        paras.append(f"{name} is a <strong>rising force</strong> in junior badminton, "
                     f"already collecting {len(wins)} tournament titles among {total_entries} career entries "
                     f"across {num_tournaments} tournaments. The trajectory is unmistakable — this is a player "
                     f"whose best chapters are still being written.")
    elif wins:
        paras.append(f"{name} broke through with a tournament title — a moment that separates "
                     f"contenders from champions. Across {total_entries} entries in {num_tournaments} tournaments, "
                     f"{first} has shown the kind of competitive fire that produces breakthroughs, "
                     f"and there are surely more titles ahead.")
    elif len(finals) >= 3:
        paras.append(f"{name} is <strong>relentlessly knocking on the door</strong>, "
                     f"with {len(finals)} Finals appearances across {total_entries} entries in "
                     f"{num_tournaments} tournaments. A player who reaches this many finals has the game to win — "
                     f"it's only a matter of time before the breakthrough arrives.")
    elif finals:
        paras.append(f"{name} has reached the <strong>Finals</strong> {len(finals)} time{'s' if len(finals) > 1 else ''}, "
                     f"proving the ability to compete at the very highest level. "
                     f"With {total_entries} entries across {num_tournaments} tournaments, "
                     f"{first} is building a body of work that points toward big things ahead.")
    elif len(semis) >= 3:
        paras.append(f"{name} is a <strong>consistent semifinalist</strong> who has reached the final four "
                     f"{len(semis)} times across {total_entries} entries in {num_tournaments} tournaments. "
                     f"That kind of reliability at the top end of the draw is the hallmark of a player "
                     f"with genuine title-winning potential.")
    elif semis:
        paras.append(f"{name} has shown <strong>serious competitive teeth</strong>, reaching the semifinals "
                     f"{len(semis)} time{'s' if len(semis) > 1 else ''} among {total_entries} entries "
                     f"across {num_tournaments} tournaments. Each deep run is a signal that this player "
                     f"belongs among the contenders.")
    elif len(top8) >= 3:
        paras.append(f"{name} is a <strong>tenacious competitor</strong> with {len(top8)} quarterfinal-or-better "
                     f"finishes across {total_entries} entries in {num_tournaments} tournaments. "
                     f"The foundation is solid, and the upward trajectory is clear — deeper runs are on the horizon.")
    elif total_entries >= 20:
        paras.append(f"{name} brings <strong>dedication and resilience</strong> to the court, "
                     f"with {total_entries} career entries across {num_tournaments} tournaments. "
                     f"In a sport that rewards persistence above all else, {first}'s commitment to competition "
                     f"is laying the groundwork for future success. The experience gained from every match "
                     f"is an investment that compounds over time.")
    elif total_entries >= 10:
        paras.append(f"{name} is <strong>steadily building</strong> a competitive resume, "
                     f"with {total_entries} entries across {num_tournaments} tournaments. "
                     f"Every tournament adds experience, every match sharpens the game, "
                     f"and the results will follow the effort.")
    elif total_entries >= 4:
        paras.append(f"{name} is in the <strong>early chapters</strong> of what promises to be "
                     f"an exciting competitive journey, with {total_entries} entries across {num_tournaments} tournaments. "
                     f"The willingness to step onto the court and compete is where every great player starts.")
    else:
        paras.append(f"{name} is <strong>just getting started</strong> on the junior badminton circuit "
                     f"with {total_entries} tournament entr{'y' if total_entries == 1 else 'ies'}. "
                     f"Every champion's story has a beginning, and this is {first}'s.")

    # === PLAYING STYLE / DISCIPLINE PROFILE ===
    if len(events_played) >= 3:
        disc_parts = []
        if s_wins: disc_parts.append(f"{len(s_wins)} singles title{'s' if len(s_wins) > 1 else ''}")
        elif s_results and best_singles <= 4: disc_parts.append(f"a singles best of #{best_singles}")
        if d_wins: disc_parts.append(f"{len(d_wins)} doubles title{'s' if len(d_wins) > 1 else ''}")
        elif d_results and best_doubles <= 4: disc_parts.append(f"a doubles best of #{best_doubles}")
        if x_wins: disc_parts.append(f"{len(x_wins)} mixed doubles title{'s' if len(x_wins) > 1 else ''}")
        elif x_results and best_mixed <= 4: disc_parts.append(f"a mixed doubles best of #{best_mixed}")

        if disc_parts:
            paras.append(f"<strong>A true triple-threat</strong>, {first} competes across singles, doubles, and mixed doubles — "
                         f"boasting " + ", ".join(disc_parts) + ". "
                         f"The ability to excel in all three disciplines reveals a player with both "
                         f"the individual brilliance to dominate rallies and the court sense to thrive with a partner.")
        else:
            paras.append(f"{first} is a <strong>versatile competitor</strong> who takes the court in singles, doubles, and mixed doubles. "
                         f"That willingness to compete across all disciplines builds a well-rounded game "
                         f"that many specialists simply cannot match.")
    elif len(events_played) == 2:
        if 'singles' in events_played and ('doubles' in events_played or 'mixed' in events_played):
            other = 'doubles' if 'doubles' in events_played else 'mixed doubles'
            if s_wins and (d_wins or x_wins):
                paras.append(f"{first} is dangerous in both singles and {other}, "
                             f"with titles in each discipline. That dual-threat capability makes "
                             f"{first} a nightmare matchup for any opponent.")
            else:
                paras.append(f"Competing in both singles and {other}, {first} is developing the kind of "
                             f"well-rounded game that pays dividends as the competition intensifies at higher levels.")
        elif 'doubles' in events_played and 'mixed' in events_played:
            paras.append(f"{first} is a <strong>doubles specialist</strong>, competing in both same-gender and mixed doubles. "
                         f"That kind of court awareness and partner chemistry is a rare and valuable skill set.")
    elif 'singles' in events_played and len(s_results) >= 3:
        if s_wins:
            paras.append(f"{first} is a <strong>singles specialist</strong> with {len(s_wins)} title{'s' if len(s_wins) > 1 else ''} — "
                         f"a player who relishes the pressure of going one-on-one with nothing to hide behind. "
                         f"In singles, every point is earned, and {first} has proven capable of earning them when it matters most.")
        else:
            paras.append(f"{first} competes primarily in <strong>singles</strong>, taking on the unique challenge of "
                         f"standing alone on the court. That mental toughness is forged one match at a time.")

    # === SIGNATURE RESULTS ===
    sig_parts = []
    if national_wins:
        nat_events = list(set(r['event'] for r in national_wins))
        sig_parts.append(f"National Champion in {', '.join(nat_events)}")
    if national_finals:
        nat_f_events = list(set(r['event'] for r in national_finals if int(r['rank_lo']) == 2))
        if nat_f_events:
            sig_parts.append(f"National Finalist in {', '.join(nat_f_events)}")
    if orc_wins:
        orc_w_tourns = list(set(r['tournament'] for r in orc_wins))
        sig_parts.append(f"{len(orc_wins)} ORC title{'s' if len(orc_wins) > 1 else ''} (across {len(orc_w_tourns)} tournament{'s' if len(orc_w_tourns) > 1 else ''})")
    if selection_podiums:
        best_sel = min(int(r['rank_lo']) for r in selection_podiums)
        sig_parts.append(f"U.S. Selection Event top-{best_sel} finisher")

    if sig_parts:
        paras.append("<strong>Signature achievements:</strong> " + " &bull; ".join(sig_parts) + ".")

    # === PARTNERSHIPS ===
    if top_partners and len(top_partners) >= 1:
        partner_paras = []
        for p, info in top_partners[:3]:
            count = info['count']
            p_wins = info['wins']
            p_best = info['best']
            p_events = info['events']
            event_types = "/".join(sorted(p_events))
            if p_wins >= 2:
                partner_paras.append(f"<strong>{p}</strong> — {count} events together in {event_types}, "
                                    f"producing an outstanding {p_wins} titles")
            elif p_wins == 1:
                partner_paras.append(f"<strong>{p}</strong> — {count} events, {p_wins} title together in {event_types}")
            elif count >= 4:
                best_str = f"best result: #{p_best}" if p_best <= 8 else ""
                partner_paras.append(f"<strong>{p}</strong> — a trusted {event_types} partner ({count} events"
                                    + (f", {best_str}" if best_str else "") + ")")
            elif count >= 2 and p_best <= 4:
                partner_paras.append(f"<strong>{p}</strong> — {count} events in {event_types}, best: #{p_best}")

        if partner_paras:
            if num_partners >= 5:
                intro = (f"{first} has demonstrated remarkable <strong>doubles adaptability</strong>, "
                         f"partnering with {num_partners} different players across the career. Key partnerships:")
            elif num_partners >= 3:
                intro = f"{first} has built strong chemistry with several partners:"
            else:
                intro = f"In doubles, {first} has formed effective partnerships:"
            paras.append(intro + "<br>" + "<br>".join("&nbsp;&nbsp;&bull; " + pp for pp in partner_paras))

    # === TRAJECTORY / TREND ===
    if len(season_keys) >= 2 and recent_results:
        recent_t = len(set(r['tournament'] for r in recent_results))
        if len(recent_wins) > len(earlier_wins) and recent_wins:
            paras.append(f"The <strong>{recent_season} season</strong> has been a step up, "
                         f"with {len(recent_wins)} title{'s' if len(recent_wins) > 1 else ''} "
                         f"across {recent_t} tournaments — an improvement that shows "
                         f"{first} is still ascending. The best may yet be ahead.")
        elif recent_wins and not earlier_wins:
            paras.append(f"The <strong>{recent_season} season</strong> brought a breakthrough — "
                         f"{first}'s first title{'s' if len(recent_wins) > 1 else ''}! "
                         f"That kind of progression from contender to champion is exactly the trajectory "
                         f"coaches dream about.")
        elif len(recent_podiums) >= 5:
            paras.append(f"The <strong>{recent_season} season</strong> has been outstanding, "
                         f"with {len(recent_podiums)} podium finishes across {recent_t} tournaments. "
                         f"{first} is playing some of the best badminton of the career right now.")
        elif recent_results and not recent_wins and earlier_wins:
            # Moving up in age group?
            recent_ags = set()
            earlier_ags = set()
            for r in recent_results:
                for ag in ['U11','U13','U15','U17','U19']:
                    if ag in r['event']: recent_ags.add(ag)
            for r in earlier_results:
                for ag in ['U11','U13','U15','U17','U19']:
                    if ag in r['event']: earlier_ags.add(ag)
            new_ags = recent_ags - earlier_ags
            if new_ags:
                paras.append(f"Having moved up to <strong>{'/'.join(sorted(new_ags, key=lambda x: int(x[1:])))}</strong>, "
                             f"{first} is navigating the challenge of tougher competition at the higher age group. "
                             f"The adjustment period is natural — and with the pedigree {first} brings, "
                             f"a return to the top is a matter of when, not if.")

    # === AGE GROUP JOURNEY ===
    if len(ag_sorted) >= 3:
        paras.append(f"<strong>A veteran of the junior circuit</strong>, {first} has competed across "
                     f"{', '.join(ag_sorted[:-1])} and {ag_sorted[-1]}, accumulating invaluable experience "
                     f"at every age group. That depth of competitive history is an asset that "
                     f"younger opponents simply cannot replicate.")
    elif len(ag_sorted) == 2:
        paras.append(f"{first} has competed at both <strong>{ag_sorted[0]}</strong> and <strong>{ag_sorted[1]}</strong>, "
                     f"showing the adaptability needed to thrive as the competition grows fiercer with each age group.")

    # === GEOGRAPHIC REACH ===
    if len(regions) >= 4:
        paras.append(f"{first} has competed across <strong>{len(regions)} different regions</strong> of the country "
                     f"({', '.join(sorted(regions))}), demonstrating a willingness to travel and test "
                     f"the game against diverse styles of play from coast to coast.")
    elif len(regions) >= 3:
        paras.append(f"With tournaments spanning {', '.join(sorted(regions))}, "
                     f"{first} isn't afraid to compete outside the home region — "
                     f"and that exposure to different playing styles only sharpens the game.")

    # === SEEDING RECOGNITION ===
    if len(top_seeds) >= 5:
        paras.append(f"{first} has been <strong>seeded #1 or #2</strong> in {len(top_seeds)} events — "
                     f"a recognition by tournament committees that this player is among the very best "
                     f"in the draw. That target on the back only makes the victories more impressive.")
    elif len(seeded_entries) >= 5:
        paras.append(f"With {len(seeded_entries)} seeded entries across the career, {first} consistently earns "
                     f"the respect of tournament committees — a testament to the results put up on the court.")

    # === CLOSING ===
    if len(seasons) >= 4 and wins:
        paras.append(f"With <strong>{len(seasons)} seasons</strong> of competitive experience and {len(wins)} title{'s' if len(wins) != 1 else ''} "
                     f"to show for it, {first} is a battle-hardened competitor whose journey is a testament "
                     f"to what dedication, talent, and love for the game can produce.")
    elif len(seasons) >= 3:
        paras.append(f"With {len(seasons)} seasons of competitive experience under the belt, "
                     f"{first} brings the kind of <strong>tournament-tested composure</strong> that "
                     f"only comes from years of stepping onto the court and competing against the best.")
    elif len(seasons) >= 2 and total_entries >= 10:
        paras.append(f"Now in the {len(seasons)}{'nd' if len(seasons)==2 else 'rd'} season of competition, "
                     f"{first}'s journey is gathering momentum with every tournament. The future is bright.")

    return "\n".join(f"<p>{p}</p>" for p in paras)


# ── Build player data for JSON ────────────────────────────────────────────────
def build_player_data(name, results):
    """Build a JSON-serializable dict for a player."""
    results_sorted = sorted(results, key=lambda r: r['dates'].split('/')[0])
    seasons = defaultdict(list)
    for r in results_sorted:
        seasons[get_season(r['dates'].split('/')[0])].append(r)

    summary = generate_summary(name, results)

    month_names = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                   'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

    wins = sum(1 for r in results if int(r['rank_lo']) == 1)
    finals_count = sum(1 for r in results if int(r['rank_lo']) == 2)
    semis_count = sum(1 for r in results if int(r['rank_lo']) in [3, 4])
    tournaments = len(set(r['tournament'] for r in results))

    # Build season rows
    season_data = {}
    for season in sorted(seasons.keys()):
        rows = []
        for r in seasons[season]:
            start = r['dates'].split('/')[0]
            y, m, d = start.split('-')
            date_str = f"{month_names[int(m)]} {y}"
            partner = parse_partner(r['player'], name) or None
            rank_str = format_rank(r['rank_lo'], r['rank_hi'])
            seed = r['seed'] if r['seed'] else ''
            rank_lo = int(r['rank_lo'])

            # Check if partner has a page
            partner_clean = clean_name(partner) if partner else None
            partner_slug = slugify(partner_clean) if partner_clean and partner_clean in unique_players else None

            rows.append({
                't': r['tournament'],
                'd': date_str,
                'e': r['event'],
                'p': partner_clean or partner,
                'ps': partner_slug,
                's': seed,
                'r': rank_str,
                'rl': rank_lo,
                'el': r['elim_round'],
            })
        season_data[season] = rows

    return {
        'name': name,
        'slug': slugify(name),
        'summary': summary,
        'stats': {
            'wins': wins,
            'finals': finals_count,
            'semis': semis_count,
            'tournaments': tournaments,
            'seasons': len(seasons),
            'entries': len(results),
        },
        'seasons': season_data,
    }


# ── Generate JSON files by first letter ──────────────────────────────────────
print(f"Building data for {len(unique_players)} players...")
# Group players by first letter of slug
letter_groups = defaultdict(dict)
count = 0
for name in sorted(unique_players):
    results = player_results.get(name, [])
    if not results:
        continue
    slug = slugify(name)
    letter = slug[0] if slug and slug[0].isalpha() else '_'
    data = build_player_data(name, results)
    letter_groups[letter][slug] = data
    count += 1
    if count % 500 == 0:
        print(f"  {count} players processed...")

# Write JSON files
for letter, players in sorted(letter_groups.items()):
    out_path = os.path.join(JSON_DIR, f"players_{letter}.json")
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(players, f, ensure_ascii=False)

print(f"Done! {count} players saved to {len(letter_groups)} JSON files in {JSON_DIR}/")

# ── Save player slug mapping for generate_html.py ───────────────────────────
with open('data/player_slugs.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['name', 'slug'])
    for name in sorted(unique_players):
        if player_results.get(name):
            w.writerow([name, slugify(name)])
print(f"Slug mapping saved to data/player_slugs.csv")

# ── Generate single player.html template ─────────────────────────────────────
PLAYER_HTML = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Player — USA Badminton Junior Results</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f7fa; color: #333; }
.header { background: linear-gradient(135deg, #1a3a5c, #2d6aa0); color: white; padding: 24px 20px; }
.header h1 { font-size: 26px; margin-bottom: 4px; }
.header p { opacity: 0.8; font-size: 14px; }
.back-link { color: rgba(255,255,255,0.8); text-decoration: none; font-size: 14px; display: inline-block; margin-bottom: 8px; }
.back-link:hover { color: white; }
.container { max-width: 1000px; margin: 0 auto; padding: 20px; }
.stats-bar { display: flex; gap: 16px; margin: 16px 0; flex-wrap: wrap; }
.stat-box { background: white; border-radius: 8px; padding: 16px 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); text-align: center; flex: 1; min-width: 100px; }
.stat-box .num { font-size: 28px; font-weight: 700; color: #2d6aa0; }
.stat-box .label { font-size: 12px; color: #888; text-transform: uppercase; letter-spacing: 0.5px; }
.stat-box.gold .num { color: #d4a017; }
.summary { background: white; border-radius: 8px; padding: 24px; margin: 16px 0; box-shadow: 0 1px 3px rgba(0,0,0,0.1); line-height: 1.7; }
.summary p { margin-bottom: 12px; }
.summary p:last-child { margin-bottom: 0; }
.disclaimer { background: #fef9e7; border: 1px solid #f0e0a0; border-radius: 6px; padding: 10px 16px; margin: 12px 0; font-size: 12px; color: #856404; }
.season-header { font-size: 18px; font-weight: 700; color: #1a3a5c; margin: 24px 0 8px; padding-bottom: 4px; border-bottom: 2px solid #2d6aa0; }
table { width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 16px; }
th { background: #1a3a5c; color: white; padding: 10px 12px; text-align: left; font-size: 13px; font-weight: 600; }
td { padding: 8px 12px; border-bottom: 1px solid #f0f0f0; font-size: 14px; }
tr:hover { background: #f8fbff; }
tr.winner { background: #fef9e7; }
tr.winner:hover { background: #fdf0c8; }
.rank-1 { color: #d4a017; font-weight: 700; }
.rank-top { color: #1a3a5c; font-weight: 700; }
.rank-mid { color: #555; }
.loading { text-align: center; padding: 60px 20px; color: #888; font-size: 18px; }
@media (max-width: 768px) {
  .stats-bar { gap: 8px; }
  .stat-box { padding: 12px; }
  .stat-box .num { font-size: 22px; }
  td, th { padding: 6px 8px; font-size: 13px; }
}
</style>
</head>
<body>
<div class="header">
  <a href="index.html" class="back-link">&larr; Back to Rankings</a>
  <h1 id="playerName">Loading...</h1>
  <p id="playerSubtitle"></p>
</div>
<div class="container" id="content">
  <div class="loading" id="loading">Loading player data...</div>
</div>
<script>
(function() {
  const params = new URLSearchParams(window.location.search);
  const slug = params.get('id');
  if (!slug) { document.getElementById('loading').textContent = 'No player specified.'; return; }

  const letter = slug[0].match(/[a-z]/) ? slug[0] : '_';
  const jsonUrl = 'data/players/players_' + letter + '.json';

  fetch(jsonUrl).then(r => { if (!r.ok) throw new Error('Not found'); return r.json(); }).then(data => {
    const p = data[slug];
    if (!p) { document.getElementById('loading').textContent = 'Player not found.'; return; }
    render(p);
  }).catch(err => {
    document.getElementById('loading').textContent = 'Could not load player data.';
  });

  function esc(s) {
    const d = document.createElement('div'); d.textContent = s || ''; return d.innerHTML;
  }

  function render(p) {
    document.title = p.name + ' \u2014 USA Badminton Junior Results';
    document.getElementById('playerName').textContent = p.name;
    document.getElementById('playerSubtitle').textContent = p.stats.entries + ' results across ' + p.stats.tournaments + ' tournaments';

    const s = p.stats;
    let html = '<div class="stats-bar">' +
      '<div class="stat-box gold"><div class="num">' + s.wins + '</div><div class="label">Titles</div></div>' +
      '<div class="stat-box"><div class="num">' + s.finals + '</div><div class="label">Finals</div></div>' +
      '<div class="stat-box"><div class="num">' + s.semis + '</div><div class="label">Semifinals</div></div>' +
      '<div class="stat-box"><div class="num">' + s.tournaments + '</div><div class="label">Tournaments</div></div>' +
      '<div class="stat-box"><div class="num">' + s.seasons + '</div><div class="label">Seasons</div></div>' +
      '</div>';

    html += '<div class="summary">' + p.summary + '</div>';
    html += '<div class="disclaimer">\u26a0 This summary is AI-generated based on tournament draw data. Results may contain errors due to name parsing in doubles events, age group splits across venues, or data entry variations. Always verify with official USA Badminton records.</div>';

    const seasonKeys = Object.keys(p.seasons).sort();
    for (const season of seasonKeys) {
      html += '<div class="season-header">Season ' + esc(season) + '</div>';
      html += '<table><tr><th>Tournament</th><th>Date</th><th>Event</th><th>Partner</th><th>Seed</th><th>Rank</th><th>Round</th></tr>';
      for (const r of p.seasons[season]) {
        const rc = r.rl === 1 ? ' class="winner"' : '';
        let rankCell;
        if (r.rl === 1) rankCell = '<span class="rank-1">\ud83c\udfc6 ' + esc(r.r) + '</span>';
        else if (r.rl <= 4) rankCell = '<span class="rank-top">' + esc(r.r) + '</span>';
        else rankCell = '<span class="rank-mid">' + esc(r.r) + '</span>';

        let partnerCell;
        if (r.ps) partnerCell = '<a href="player.html?id=' + r.ps + '" style="color:#2d6aa0;text-decoration:none">' + esc(r.p) + '</a>';
        else if (r.p) partnerCell = esc(r.p);
        else partnerCell = '\u2014';

        html += '<tr' + rc + '><td>' + esc(r.t) + '</td><td>' + esc(r.d) + '</td><td>' + esc(r.e) + '</td>' +
          '<td>' + partnerCell + '</td><td>' + esc(r.s) + '</td><td>' + rankCell + '</td><td>' + esc(r.el) + '</td></tr>';
      }
      html += '</table>';
    }

    html += '<div class="disclaimer" style="margin-top:24px;">Data sourced from <a href="https://www.tournamentsoftware.com" style="color:#856404">tournamentsoftware.com</a> via USA Badminton tournament draws. Player pages generated automatically \u2014 report issues at the source.</div>';

    document.getElementById('content').innerHTML = html;
  }
})();
</script>
</body>
</html>'''

with open('player.html', 'w', encoding='utf-8') as f:
    f.write(PLAYER_HTML)
print("Generated player.html template")
