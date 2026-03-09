"""Generate player data JSON files + a single player.html template.

Instead of 3,833 individual HTML files, we output:
  - data/players/players_a.json .. players_z.json (+ players_other.json)
  - player.html (single template that loads JSON client-side via ?id=slug)
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import csv, os, re, json, random
from collections import defaultdict, Counter
from html import escape

DRAWS_DIR = "data/draws"
JSON_DIR = "data/players"
os.makedirs(JSON_DIR, exist_ok=True)

# ── State/region mappings ─────────────────────────────────────────────────────
STATE_NAMES = {
    'AL':'Alabama','AK':'Alaska','AZ':'Arizona','AR':'Arkansas','CA':'California',
    'CO':'Colorado','CT':'Connecticut','DE':'Delaware','FL':'Florida','GA':'Georgia',
    'HI':'Hawaii','ID':'Idaho','IL':'Illinois','IN':'Indiana','IA':'Iowa',
    'KS':'Kansas','KY':'Kentucky','LA':'Louisiana','ME':'Maine','MD':'Maryland',
    'MA':'Massachusetts','MI':'Michigan','MN':'Minnesota','MS':'Mississippi',
    'MO':'Missouri','MT':'Montana','NE':'Nebraska','NV':'Nevada','NH':'New Hampshire',
    'NJ':'New Jersey','NM':'New Mexico','NY':'New York','NC':'North Carolina',
    'ND':'North Dakota','OH':'Ohio','OK':'Oklahoma','OR':'Oregon','PA':'Pennsylvania',
    'RI':'Rhode Island','SC':'South Carolina','SD':'South Dakota','TN':'Tennessee',
    'TX':'Texas','UT':'Utah','VT':'Vermont','VA':'Virginia','WA':'Washington',
    'WV':'West Virginia','WI':'Wisconsin','WY':'Wyoming','DC':'Washington D.C.',
}
STATE_REGIONS = {
    'WA':'Pacific Northwest','OR':'Pacific Northwest','ID':'Pacific Northwest',
    'CA':'California','HI':'Pacific',
    'TX':'Texas','OK':'Southern','AR':'Southern','LA':'Southern',
    'FL':'Southern','GA':'Southern','SC':'Southern','NC':'Southern',
    'VA':'Mid-Atlantic','MD':'Mid-Atlantic','DC':'Mid-Atlantic','DE':'Mid-Atlantic',
    'NJ':'Northeast','NY':'Northeast','CT':'Northeast','RI':'Northeast',
    'MA':'Northeast','NH':'Northeast','VT':'Northeast','ME':'Northeast','PA':'Northeast',
    'IL':'Midwest','WI':'Midwest','MN':'Midwest','IA':'Midwest','MO':'Midwest',
    'IN':'Midwest','MI':'Midwest','OH':'Midwest',
    'CO':'Mountain West','UT':'Mountain West','AZ':'Mountain West','NV':'Mountain West','NM':'Mountain West',
    'TN':'Southern','AL':'Southern','MS':'Southern','KY':'Southern',
    'KS':'Midwest','NE':'Midwest','SD':'Midwest','ND':'Midwest',
    'MT':'Mountain West','WY':'Mountain West',
}

# ── Load all results ─────────────────────────────────────────────────────────
def load_all_results():
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
    return re.sub(r'\s*\[[\w/]*\]', '', raw).replace('*', '').strip()

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

def tournament_tier(tournament_name):
    if 'Selection' in tournament_name: return 'SEL'
    if 'National' in tournament_name: return 'JN'
    if 'ORC' in tournament_name: return 'ORC'
    if 'CRC' in tournament_name: return 'CRC'
    return 'OLC'

TIER_LABELS = {'SEL': 'U.S. Selection Event', 'JN': 'Junior Nationals', 'ORC': 'Open Regional Championship', 'CRC': 'Club Regional Championship', 'OLC': 'Open Local Championship'}
TIER_RANK = {'SEL': 4, 'JN': 3, 'ORC': 2, 'CRC': 1, 'OLC': 0}

def is_singles(event):
    return event.startswith('BS') or event.startswith('GS') or 'Singles' in event

def is_doubles(event):
    return event.startswith('BD') or event.startswith('GD')

def is_mixed(event):
    return event.startswith('XD') or 'Mixed' in event

def get_age_group(event):
    for ag in ['U11', 'U13', 'U15', 'U17', 'U19']:
        if ag in event:
            return ag
    return None

def get_home_state(results, player_name):
    """Extract home state from singles entries (most frequent)."""
    states = []
    for r in results:
        if is_singles(r['event']) and r.get('state') and len(r['state']) == 2:
            states.append(r['state'])
    if not states:
        return None
    return Counter(states).most_common(1)[0][0]

# ── Load game stats ──────────────────────────────────────────────────────────
game_stats = {}
try:
    with open('data/player_game_stats.csv', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            game_stats[row['player']] = row
except FileNotFoundError:
    pass

# ── Load all results & build player index ────────────────────────────────────
print("Loading all results...")
all_results = load_all_results()
print(f"  {len(all_results)} total rows")

player_names = set()
for r in all_results:
    event = r['event']
    if event.startswith('BS') or event.startswith('GS') or 'Singles' in event:
        name = clean_name(r['player'])
        if name and name.lower() != 'bye':
            player_names.add(name)

name_variants = defaultdict(list)
for n in player_names:
    name_variants[n.lower()].append(n)

canonical_names = {}
for lower, variants in name_variants.items():
    best = max(variants, key=lambda v: sum(1 for r in all_results if v in r['player']))
    for v in variants:
        canonical_names[v] = best

unique_players = set(canonical_names.values())
print(f"  {len(unique_players)} unique players")

# ── Collect results per player ───────────────────────────────────────────────
print("Collecting per-player results...")
player_results = defaultdict(list)
# Sort unique_players longest-first so we can match greedily
sorted_players = sorted(unique_players, key=len, reverse=True)
for r in all_results:
    raw = r['player']
    raw_clean = clean_name(raw)
    # Find which players appear in this entry by removing matched names
    remaining = raw_clean
    matched = []
    for name in sorted_players:
        if name in remaining:
            matched.append(name)
            remaining = remaining.replace(name, '', 1)
    for name in matched:
        player_results[name].append(r)


# ── Generate summary ─────────────────────────────────────────────────────────
def generate_summary(name, results):
    """Generate a personalized, dramatic, positive summary using per-player RNG for variety."""
    if not results:
        return f"<p>{name} is building their tournament journey.</p>"

    rng = random.Random(hash(name))  # deterministic per player
    first = name.split()[0]
    results_sorted = sorted(results, key=lambda r: r['dates'].split('/')[0])

    # ── Collect all stats ─────────────────────────────────────────────────
    seasons = defaultdict(list)
    for r in results_sorted:
        seasons[get_season(r['dates'].split('/')[0])].append(r)
    season_keys = sorted(seasons.keys())

    total_entries = len(results)
    all_tournaments = sorted(set(r['tournament'] for r in results))
    num_tournaments = len(all_tournaments)

    wins = [r for r in results if int(r['rank_lo']) == 1]
    finals = [r for r in results if int(r['rank_lo']) == 2]
    semis = [r for r in results if int(r['rank_lo']) in [3, 4]]
    top8 = [r for r in results if int(r['rank_lo']) <= 8]

    # Tier-specific results
    tier_results = defaultdict(list)
    tier_wins = defaultdict(list)
    tier_podiums = defaultdict(list)
    for r in results:
        t = tournament_tier(r['tournament'])
        tier_results[t].append(r)
        if int(r['rank_lo']) == 1: tier_wins[t].append(r)
        if int(r['rank_lo']) <= 4: tier_podiums[t].append(r)

    sel_results = tier_results.get('SEL', [])
    sel_podiums = tier_podiums.get('SEL', [])
    jn_results = tier_results.get('JN', [])
    jn_wins = tier_wins.get('JN', [])
    jn_podiums = tier_podiums.get('JN', [])
    orc_results = tier_results.get('ORC', [])
    orc_wins = tier_wins.get('ORC', [])
    orc_podiums = tier_podiums.get('ORC', [])

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

    # Age groups
    age_groups = set()
    for r in results:
        ag = get_age_group(r['event'])
        if ag: age_groups.add(ag)
    ag_sorted = sorted(age_groups, key=lambda x: int(x[1:]))

    current_ag = None
    for r in reversed(results_sorted):
        current_ag = get_age_group(r['event'])
        if current_ag: break

    # Playing up detection: same tournament, multiple age groups
    playing_up_count = 0
    tourn_ags = defaultdict(set)
    for r in results:
        ag = get_age_group(r['event'])
        if ag: tourn_ags[r['tournament']].add(ag)
    for t, ags in tourn_ags.items():
        if len(ags) >= 2:
            playing_up_count += 1

    # State/region
    home_state = get_home_state(results, name)
    home_region = STATE_REGIONS.get(home_state) if home_state else None
    home_state_name = STATE_NAMES.get(home_state) if home_state else None

    # Seeding
    seeded_entries = [r for r in results if r['seed'] and r['seed'] not in ['', 'WC']]
    top_seeds = [r for r in seeded_entries if r['seed'] in ['1', '2']]

    # Trends
    recent_season = season_keys[-1] if season_keys else None
    recent_results = seasons.get(recent_season, []) if recent_season else []
    recent_wins = [r for r in recent_results if int(r['rank_lo']) == 1]
    recent_podiums = [r for r in recent_results if int(r['rank_lo']) <= 4]
    earlier_season = season_keys[-2] if len(season_keys) >= 2 else None
    earlier_results = seasons.get(earlier_season, []) if earlier_season else []
    earlier_wins = [r for r in earlier_results if int(r['rank_lo']) == 1]

    # Partners — track recency and seasons
    partners = defaultdict(lambda: {'count': 0, 'wins': 0, 'events': set(), 'best': 999,
                                     'seasons': set(), 'last_date': '', 'recent_count': 0, 'recent_wins': 0})
    recent_two = set(season_keys[-2:]) if len(season_keys) >= 2 else set(season_keys[-1:]) if season_keys else set()
    for r in results_sorted:
        if is_singles(r['event']): continue
        p = parse_partner(r['player'], name)
        if p:
            partners[p]['count'] += 1
            partners[p]['events'].add(r['event'].split()[0] if ' ' in r['event'] else r['event'][:2])
            rank_lo = int(r['rank_lo'])
            if rank_lo == 1: partners[p]['wins'] += 1
            if rank_lo < partners[p]['best']: partners[p]['best'] = rank_lo
            start_date = r['dates'].split('/')[0]
            s = get_season(start_date)
            partners[p]['seasons'].add(s)
            if start_date > partners[p]['last_date']:
                partners[p]['last_date'] = start_date
            if s in recent_two:
                partners[p]['recent_count'] += 1
                if rank_lo == 1: partners[p]['recent_wins'] += 1
    # Sort by: current partner first, then by recency-weighted count
    def partner_sort_key(item):
        p, info = item
        is_current = 1 if (recent_season and recent_season in info['seasons']) else 0
        return (-is_current, -info['recent_count'], -info['count'])
    top_partners = sorted(partners.items(), key=partner_sort_key)
    num_partners = len(partners)

    # Regional diversity
    regions = set()
    for t in all_tournaments:
        for region in ['NW', 'NE', 'SoCal', 'NorCal', 'South', 'Midwest']:
            if region in t: regions.add(region); break

    # Game stats
    gstats = game_stats.get(name)

    # ── Build paragraphs ─────────────────────────────────────────────────
    paras = []

    # === OPENING — tier-aware identity ===
    highest_tier = 'OLC'
    for t in ['SEL', 'JN', 'ORC', 'CRC']:
        if tier_results.get(t):
            highest_tier = t
            break

    # State intro clause (used in opening for personalization)
    state_intro = ""
    if home_state_name:
        state_phrases = [
            f"Hailing from <strong>{home_state_name}</strong>, ",
            f"Representing <strong>{home_state_name}</strong>, ",
            f"Out of <strong>{home_state_name}</strong>, ",
            f"A <strong>{home_state_name}</strong> competitor, ",
        ]
        state_intro = rng.choice(state_phrases)

    # Age intro clause
    ag_intro = ""
    if current_ag:
        ag_intro = f"currently competing at the <strong>{current_ag}</strong> level, "

    if sel_podiums:
        best_sel = min(int(r['rank_lo']) for r in sel_podiums)
        sel_events = list(set(r['event'] for r in sel_podiums))
        if best_sel == 1:
            paras.append(f"{state_intro}{name} has reached the pinnacle of American junior badminton — "
                         f"<strong>selected for the U.S. Junior National Team</strong>. "
                         f"Winning at the Selection Event ({', '.join(sel_events)}) is the ultimate validation: "
                         f"it means being chosen to represent the country on the international stage. "
                         f"With {len(wins)} career titles across {num_tournaments} tournaments, "
                         f"this is a player who delivers when everything is on the line.")
        elif best_sel <= 4:
            paras.append(f"{state_intro}{name} is among the <strong>elite few</strong> to reach the podium "
                         f"at the U.S. Selection Event — the tournament that determines who represents America internationally. "
                         f"A top-{best_sel} finish at Selection places {first} in the rarest company in U.S. junior badminton.")
        else:
            paras.append(f"{state_intro}{name} has competed at the <strong>U.S. Selection Event</strong>, "
                         f"the most prestigious tournament in American junior badminton. "
                         f"Simply earning entry signals that {first} is recognized as one of the nation's top junior players.")
    elif jn_wins:
        nat_win_events = list(set(r['event'] for r in jn_wins))
        openers = [
            f"{state_intro}{name} is a <strong>U.S. Junior National Champion</strong> — "
            f"crowned at the biggest event on the domestic calendar",
            f"{state_intro}{name} has climbed to the top of the mountain at <strong>Junior Nationals</strong>, "
            f"the crown jewel of the American junior badminton season",
            f"{state_intro}{name} wears the gold from <strong>Junior Nationals</strong> — "
            f"the single most important tournament for any American junior player",
        ]
        opener = rng.choice(openers)
        if len(jn_wins) >= 3:
            paras.append(f"{opener}. With <strong>{len(jn_wins)} national titles</strong> ({', '.join(nat_win_events)}), "
                         f"{first} has built a legacy of dominance at the highest level of the sport. "
                         f"Across {total_entries} career entries in {num_tournaments} tournaments, "
                         f"{first} has amassed {len(wins)} total victories — a record that speaks for itself.")
        else:
            paras.append(f"{opener} in {', '.join(nat_win_events)}. "
                         f"That title represents the culmination of grueling competition against the very best in the country. "
                         f"With {len(wins)} career victories across {num_tournaments} tournaments, "
                         f"{first} has proven the ability to deliver when it matters most.")
    elif jn_podiums:
        best_jn = min(int(r['rank_lo']) for r in jn_podiums)
        jn_p_events = list(set(r['event'] for r in jn_podiums))
        if best_jn == 2:
            paras.append(f"{state_intro}{name} is a <strong>Junior Nationals finalist</strong> — "
                         f"one match away from the biggest title in American junior badminton. "
                         f"Reaching the finals at Nationals ({', '.join(jn_p_events)}) puts {first} "
                         f"in an incredibly select group, and the experience of competing at that level is invaluable.")
        else:
            paras.append(f"{state_intro}{name} has reached the <strong>podium at Junior Nationals</strong>, "
                         f"finishing top-{best_jn} in {', '.join(jn_p_events)}. "
                         f"At the biggest event on the calendar, making the final four is a statement: "
                         f"{first} belongs with the best in the country.")
    elif orc_wins:
        orc_w_count = len(orc_wins)
        orc_w_tourns = list(set(r['tournament'] for r in orc_wins))
        openers_orc = [
            f"{state_intro}{name} is a <strong>Regional Championship titlist</strong>",
            f"{state_intro}{name} has conquered the <strong>Open Regional Championship</strong> stage",
            f"{state_intro}{name} stands as an <strong>ORC champion</strong>",
        ]
        opener = rng.choice(openers_orc)
        if orc_w_count >= 3:
            paras.append(f"{opener}, capturing an impressive <strong>{orc_w_count} ORC titles</strong> "
                         f"across {len(orc_w_tourns)} regional championships. "
                         f"ORCs are the highest level of regular-season competition, drawing the strongest fields in each region. "
                         f"Winning at this level repeatedly marks {first} as one of the premier players on the circuit.")
        else:
            paras.append(f"{opener}, {ag_intro}proving the ability to triumph against the strongest regional fields. "
                         f"Open Regional Championships draw the top talent from across the region, "
                         f"and taking home the title is a genuine achievement.")
    elif orc_podiums:
        best_orc = min(int(r['rank_lo']) for r in orc_podiums)
        paras.append(f"{state_intro}{name} has reached the <strong>podium at the ORC level</strong> "
                     f"(top-{best_orc}), {ag_intro}competing against the best players in the region. "
                     f"Open Regional Championships are a significant step up from local events, "
                     f"and {first}'s results show the readiness for top-tier competition.")
    elif len(wins) >= 5:
        openers_local = [
            f"{state_intro}{name} is a <strong>prolific winner</strong> on the junior circuit",
            f"{state_intro}{name} has established a <strong>commanding presence</strong> at the local tournament level",
            f"{state_intro}{name} is a <strong>serial champion</strong> on the local circuit",
        ]
        paras.append(f"{rng.choice(openers_local)}, {ag_intro}racking up <strong>{len(wins)} titles</strong> "
                     f"across {num_tournaments} tournaments. "
                     f"That winning pedigree at the local and club level creates the perfect launchpad "
                     f"for success at the regional and national stages.")
    elif len(wins) >= 2:
        openers_multi = [
            f"{state_intro}{name} has <strong>tasted victory multiple times</strong>",
            f"{state_intro}{name} is a <strong>multi-time champion</strong> on the junior circuit",
            f"{state_intro}{name} has <strong>collected {len(wins)} tournament titles</strong>",
        ]
        paras.append(f"{rng.choice(openers_multi)}, {ag_intro}capturing {len(wins)} titles across "
                     f"{num_tournaments} tournaments and {total_entries} entries. "
                     f"Each win is earned through bracket battles against hungry opponents — "
                     f"and {first} keeps finding ways to come out on top.")
    elif wins:
        openers_first = [
            f"{state_intro}{name} broke through with a <strong>tournament title</strong>",
            f"{state_intro}{name} knows the feeling of <strong>standing atop the podium</strong>",
            f"{state_intro}{name} has <strong>claimed a championship</strong>",
        ]
        tourn_name = wins[0]['tournament']
        tier = tournament_tier(tourn_name)
        tier_note = f" at the {TIER_LABELS[tier]} level" if tier in ['ORC', 'JN'] else ""
        paras.append(f"{rng.choice(openers_first)}{tier_note}, {ag_intro}a moment that separates "
                     f"contenders from champions. "
                     f"With {total_entries} entries across {num_tournaments} tournaments, "
                     f"the competitive foundation is built — and more titles are within reach.")
    elif len(finals) >= 3:
        paras.append(f"{state_intro}{name} is <strong>relentlessly knocking on the door</strong>, "
                     f"{ag_intro}reaching {len(finals)} finals across {total_entries} entries. "
                     f"A player who reaches that many championship matches has all the tools — "
                     f"the breakthrough title is coming.")
    elif finals:
        paras.append(f"{state_intro}{name} has stepped onto the <strong>championship stage</strong>, "
                     f"{ag_intro}reaching the finals {len(finals)} time{'s' if len(finals) > 1 else ''}. "
                     f"With {total_entries} entries across {num_tournaments} tournaments, "
                     f"{first} is proving the ability to compete at the highest level.")
    elif len(semis) >= 3:
        paras.append(f"{state_intro}{name} is a <strong>consistent semifinalist</strong>, "
                     f"{ag_intro}reaching the final four {len(semis)} times. "
                     f"That kind of reliability at the top of the draw is the signature of a player "
                     f"who will soon be contending for titles.")
    elif semis:
        paras.append(f"{state_intro}{name} has shown <strong>real competitive teeth</strong>, "
                     f"{ag_intro}breaking into the semifinals {len(semis)} time{'s' if len(semis) > 1 else ''}. "
                     f"Across {total_entries} entries in {num_tournaments} tournaments, "
                     f"every deep run is a signal of growing strength.")
    elif len(top8) >= 3:
        phrases = [
            f"{state_intro}{name} is a <strong>tenacious competitor</strong> with {len(top8)} quarterfinal-or-better finishes",
            f"{state_intro}{name} keeps <strong>punching through to the quarterfinals</strong>, "
            f"doing so {len(top8)} times",
        ]
        paras.append(f"{rng.choice(phrases)}, {ag_intro}building a strong foundation across "
                     f"{num_tournaments} tournaments. Deeper runs are on the horizon.")
    elif total_entries >= 20:
        phrases = [
            f"{state_intro}{name} brings <strong>dedication and grit</strong> to every tournament",
            f"{state_intro}{name} is a <strong>committed competitor</strong> who keeps showing up",
            f"{state_intro}{name} embodies the <strong>relentless spirit</strong> of junior badminton",
        ]
        paras.append(f"{rng.choice(phrases)}, {ag_intro}with {total_entries} career entries "
                     f"across {num_tournaments} tournaments. "
                     f"In a sport that rewards persistence, {first}'s commitment is the ultimate investment in future success.")
    elif total_entries >= 8:
        phrases = [
            f"{state_intro}{name} is <strong>steadily building</strong> a competitive resume",
            f"{state_intro}{name} is on an <strong>upward trajectory</strong>",
        ]
        paras.append(f"{rng.choice(phrases)}, {ag_intro}with {total_entries} entries "
                     f"across {num_tournaments} tournaments. "
                     f"Every tournament adds experience, every match sharpens the game.")
    elif total_entries >= 3:
        phrases = [
            f"{state_intro}{name} is in the <strong>early chapters</strong> of a competitive journey",
            f"{state_intro}{name} is <strong>writing the opening pages</strong> of a badminton story",
        ]
        paras.append(f"{rng.choice(phrases)}, {ag_intro}with {total_entries} entries "
                     f"across {num_tournaments} tournaments. "
                     f"The willingness to compete is where every great player starts.")
    else:
        phrases = [
            f"{state_intro}{name} is <strong>just getting started</strong> on the junior circuit",
            f"{state_intro}{name} has <strong>stepped onto the competitive stage</strong>",
        ]
        paras.append(f"{rng.choice(phrases)} "
                     f"with {total_entries} tournament entr{'y' if total_entries == 1 else 'ies'}. "
                     f"Every champion's story has a beginning, and this is {first}'s.")

    # === PLAYING UP ===
    if playing_up_count >= 3:
        paras.append(f"{first} is known for <strong>playing up</strong>, regularly entering higher age groups "
                     f"and testing against older, more experienced opponents ({playing_up_count} tournaments "
                     f"with multi-age-group entries). That willingness to seek out tougher competition "
                     f"accelerates development in ways that playing it safe never can.")
    elif playing_up_count >= 1:
        paras.append(f"Notably, {first} has entered <strong>higher age groups</strong> at "
                     f"{playing_up_count} tournament{'s' if playing_up_count > 1 else ''}, "
                     f"voluntarily taking on older competition — a bold move that reveals both confidence "
                     f"and a hunger for growth.")

    # === DISCIPLINE PROFILE ===
    if len(events_played) >= 3:
        disc_parts = []
        if s_wins: disc_parts.append(f"{len(s_wins)} singles title{'s' if len(s_wins) > 1 else ''}")
        elif s_results and min(int(r['rank_lo']) for r in s_results) <= 4:
            disc_parts.append(f"a singles best of #{min(int(r['rank_lo']) for r in s_results)}")
        if d_wins: disc_parts.append(f"{len(d_wins)} doubles title{'s' if len(d_wins) > 1 else ''}")
        elif d_results and min(int(r['rank_lo']) for r in d_results) <= 4:
            disc_parts.append(f"a doubles best of #{min(int(r['rank_lo']) for r in d_results)}")
        if x_wins: disc_parts.append(f"{len(x_wins)} mixed doubles title{'s' if len(x_wins) > 1 else ''}")
        elif x_results and min(int(r['rank_lo']) for r in x_results) <= 4:
            disc_parts.append(f"a mixed doubles best of #{min(int(r['rank_lo']) for r in x_results)}")

        triple_phrases = [
            f"<strong>A true triple-threat</strong>, {first} competes across singles, doubles, and mixed doubles",
            f"{first} is that rare <strong>three-discipline competitor</strong> — singles, doubles, and mixed",
            f"What makes {first} especially formidable is the <strong>versatility across all three disciplines</strong>",
        ]
        if disc_parts:
            paras.append(f"{rng.choice(triple_phrases)} — boasting {', '.join(disc_parts)}. "
                         f"The ability to excel in all three formats reveals both individual brilliance "
                         f"and the court sense to thrive alongside a partner.")
        else:
            paras.append(f"{rng.choice(triple_phrases)}. "
                         f"Competing across all disciplines builds a well-rounded game "
                         f"that pure specialists can't replicate.")
    elif len(events_played) == 2:
        if 'singles' in events_played and ('doubles' in events_played or 'mixed' in events_played):
            other = 'doubles' if 'doubles' in events_played else 'mixed doubles'
            paras.append(f"{first} competes in both <strong>singles and {other}</strong>, developing the kind of "
                         f"well-rounded game that pays dividends as competition intensifies at higher levels.")
        elif 'doubles' in events_played and 'mixed' in events_played:
            paras.append(f"{first} is a <strong>doubles specialist</strong>, competing in both same-gender "
                         f"and mixed doubles — a skill set built on court awareness and partner chemistry.")
    elif 'singles' in events_played and len(s_results) >= 3:
        if s_wins:
            paras.append(f"{first} is a <strong>singles specialist</strong> with {len(s_wins)} "
                         f"title{'s' if len(s_wins) > 1 else ''} — a player who relishes the pressure of one-on-one combat "
                         f"where there's nowhere to hide.")

    # === TOURNAMENT TIER HIGHLIGHTS ===
    sig_parts = []
    if sel_podiums:
        best_sel = min(int(r['rank_lo']) for r in sel_podiums)
        sel_events = list(set(r['event'] for r in sel_podiums))
        if best_sel == 1:
            sig_parts.append(f"<strong>U.S. Selection Event champion</strong> ({', '.join(sel_events)}) — selected to represent the USA")
        else:
            sig_parts.append(f"U.S. Selection Event top-{best_sel} ({', '.join(sel_events)})")
    if sel_results and not sel_podiums:
        sig_parts.append(f"U.S. Selection Event participant ({len(sel_results)} entr{'y' if len(sel_results) == 1 else 'ies'})")

    if jn_wins:
        jn_w_events = list(set(r['event'] for r in jn_wins))
        sig_parts.append(f"<strong>Junior Nationals champion</strong> ({', '.join(jn_w_events)})")
    elif jn_podiums:
        best_jn = min(int(r['rank_lo']) for r in jn_podiums)
        jn_p_events = list(set(r['event'] for r in jn_podiums))
        sig_parts.append(f"Junior Nationals top-{best_jn} ({', '.join(jn_p_events)})")
    elif jn_results:
        sig_parts.append(f"Junior Nationals competitor ({len(jn_results)} entr{'y' if len(jn_results) == 1 else 'ies'})")

    if orc_wins:
        orc_w_tourns = list(set(r['tournament'] for r in orc_wins))
        sig_parts.append(f"{len(orc_wins)} ORC title{'s' if len(orc_wins) > 1 else ''}")
    elif orc_podiums:
        best_orc = min(int(r['rank_lo']) for r in orc_podiums)
        sig_parts.append(f"ORC top-{best_orc} finisher")

    if sig_parts:
        paras.append("<strong>Career highlights:</strong> " + " &bull; ".join(sig_parts) + ".")

    # === GAME STATS (if available) ===
    if gstats:
        gs_parts = []
        win_pct = float(gstats.get('win_pct', 0))
        matches = int(gstats.get('matches', 0))
        three_game = int(gstats.get('three_game_matches', 0))
        three_game_wins = int(gstats.get('three_game_wins', 0))
        straight_wins = int(gstats.get('straight_set_wins', 0))
        pt_diff = int(gstats.get('pt_diff', 0))
        biggest_win = int(gstats.get('biggest_win_margin', 0))

        if win_pct >= 80:
            gs_parts.append(f"an extraordinary <strong>{win_pct:.0f}% match win rate</strong> across {matches} matches")
        elif win_pct >= 70:
            gs_parts.append(f"a commanding <strong>{win_pct:.0f}% win rate</strong> across {matches} matches")
        elif win_pct >= 60:
            gs_parts.append(f"a solid <strong>{win_pct:.0f}% win rate</strong> over {matches} matches")

        if three_game >= 5:
            if three_game_wins > three_game - three_game_wins:
                tg_pct = three_game_wins / three_game * 100
                gs_parts.append(f"a clutch <strong>{tg_pct:.0f}% win rate in three-game matches</strong> ({three_game_wins}/{three_game})")
            elif three_game >= 10:
                gs_parts.append(f"{three_game} three-game battles — proving {first} is no stranger to the pressure of a decider")

        if straight_wins >= 20:
            gs_parts.append(f"<strong>{straight_wins} straight-games victories</strong>, showing the ability to close out matches decisively")

        if pt_diff >= 500:
            gs_parts.append(f"a career <strong>+{pt_diff} point differential</strong>")
        elif pt_diff >= 200:
            gs_parts.append(f"a positive +{pt_diff} point differential across the career")

        if biggest_win >= 30:
            gs_parts.append(f"a biggest win margin of <strong>{biggest_win} points</strong>")

        # Pick 2-3 highlights to avoid overwhelming
        if len(gs_parts) > 3:
            gs_parts = rng.sample(gs_parts, 3)

        if gs_parts:
            intros = [
                f"The numbers tell a compelling story: ",
                f"Diving into the match data reveals: ",
                f"The statistics paint a vivid picture — ",
                f"Beyond the trophies, the numbers stand out: ",
            ]
            paras.append(rng.choice(intros) + f"{first} boasts " + ", ".join(gs_parts) + ".")

    # === PARTNERSHIPS ===
    if top_partners:
        partner_paras = []
        for p, info in top_partners[:4]:
            count = info['count']
            p_wins = info['wins']
            p_best = info['best']
            p_seasons = len(info['seasons'])
            is_current = recent_season and recent_season in info['seasons']
            rc = info['recent_count']
            rw = info['recent_wins']
            event_types = "/".join(sorted(info['events']))

            # Build a description emphasizing recency
            tag = ""
            if is_current and rc >= 3:
                tag = " <em>(current primary partner)</em>"
            elif is_current:
                tag = " <em>(current partner)</em>"

            longevity = ""
            if p_seasons >= 3:
                longevity = f", spanning {p_seasons} seasons"
            elif p_seasons == 2:
                longevity = f", across 2 seasons"

            if is_current and rc >= 3 and rw >= 1:
                partner_paras.append(f"<strong>{p}</strong>{tag} — {rc} events together this season alone "
                                    f"with {rw} title{'s' if rw > 1 else ''}, building serious momentum "
                                    f"({count} total events in {event_types}{longevity})")
            elif is_current and count >= 3 and p_wins >= 2:
                partner_paras.append(f"<strong>{p}</strong>{tag} — an ongoing partnership that keeps producing results: "
                                    f"{p_wins} titles across {count} events in {event_types}{longevity}")
            elif p_wins >= 2:
                partner_paras.append(f"<strong>{p}</strong>{tag} — {count} events in {event_types}, "
                                    f"producing {p_wins} titles together{longevity}")
            elif p_wins == 1:
                partner_paras.append(f"<strong>{p}</strong>{tag} — {count} events, 1 title together in {event_types}{longevity}")
            elif is_current and count >= 2:
                best_str = f", best: #{p_best}" if p_best <= 8 else ""
                partner_paras.append(f"<strong>{p}</strong>{tag} — currently teaming up in {event_types} "
                                    f"({count} events{best_str}{longevity})")
            elif count >= 4:
                best_str = f", best: #{p_best}" if p_best <= 8 else ""
                partner_paras.append(f"<strong>{p}</strong>{tag} — a trusted {event_types} partner ({count} events{best_str}{longevity})")
            elif count >= 2 and p_best <= 4:
                partner_paras.append(f"<strong>{p}</strong>{tag} — {count} events in {event_types}, best: #{p_best}{longevity}")

        if partner_paras:
            # Count current partners
            current_partners = [p for p, info in top_partners if recent_season and recent_season in info['seasons']]
            if num_partners >= 5:
                intro = rng.choice([
                    f"{first} has shown remarkable <strong>doubles adaptability</strong>, partnering with {num_partners} different players across the career:",
                    f"With {num_partners} different doubles partners over the years, {first} adapts to anyone:",
                ])
            elif num_partners >= 3:
                intro = f"{first} has built chemistry with several doubles partners:"
            else:
                intro = f"In doubles, {first} has formed effective partnerships:"
            paras.append(intro + "<br>" + "<br>".join("&nbsp;&nbsp;&bull; " + pp for pp in partner_paras))

    # === TRAJECTORY / TREND ===
    if len(season_keys) >= 2 and recent_results:
        recent_t = len(set(r['tournament'] for r in recent_results))
        if len(recent_wins) > len(earlier_wins) and recent_wins:
            phrases = [
                f"The <strong>{recent_season} season</strong> has been a step up",
                f"{first} is <strong>peaking at the right time</strong> in {recent_season}",
                f"The {recent_season} season tells a story of <strong>acceleration</strong>",
            ]
            paras.append(f"{rng.choice(phrases)}, with {len(recent_wins)} "
                         f"title{'s' if len(recent_wins) > 1 else ''} across {recent_t} tournaments — "
                         f"a clear sign that {first} is still ascending.")
        elif recent_wins and not earlier_wins:
            paras.append(f"The <strong>{recent_season} season</strong> delivered a breakthrough — "
                         f"{first}'s first title{'s' if len(recent_wins) > 1 else ''}! "
                         f"That progression from contender to champion is exactly what every player works toward.")
        elif len(recent_podiums) >= 5:
            paras.append(f"The <strong>{recent_season} season</strong> has been outstanding, "
                         f"with {len(recent_podiums)} podium finishes across {recent_t} tournaments. "
                         f"{first} is playing some of the best badminton of the career right now.")
        elif recent_results and not recent_wins and earlier_wins:
            # Moving up in age group?
            recent_ags = set()
            earlier_ags = set()
            for r in recent_results:
                ag = get_age_group(r['event'])
                if ag: recent_ags.add(ag)
            for r in earlier_results:
                ag = get_age_group(r['event'])
                if ag: earlier_ags.add(ag)
            new_ags = recent_ags - earlier_ags
            if new_ags:
                new_ag_str = '/'.join(sorted(new_ags, key=lambda x: int(x[1:])))
                paras.append(f"Having moved up to <strong>{new_ag_str}</strong>, "
                             f"{first} is navigating tougher competition at the higher age group. "
                             f"The adjustment is natural — and with the pedigree {first} brings, "
                             f"a return to the top is a matter of when, not if.")

    # === AGE GROUP JOURNEY ===
    if len(ag_sorted) >= 3:
        phrases = [
            f"<strong>A veteran of the junior circuit</strong>, {first} has competed across "
            f"{', '.join(ag_sorted[:-1])} and {ag_sorted[-1]}",
            f"{first} has been on this journey through <strong>{', '.join(ag_sorted)}</strong> — "
            f"a multi-age-group career that few can match",
        ]
        paras.append(f"{rng.choice(phrases)}, accumulating invaluable experience "
                     f"at every level. That depth of competitive history is an asset "
                     f"younger opponents simply cannot replicate.")
    elif len(ag_sorted) == 2:
        paras.append(f"{first} has competed at both <strong>{ag_sorted[0]}</strong> and "
                     f"<strong>{ag_sorted[1]}</strong>, showing the adaptability needed to thrive "
                     f"as competition grows fiercer with each age group.")

    # === GEOGRAPHIC REACH ===
    if len(regions) >= 4:
        paras.append(f"{first} has competed across <strong>{len(regions)} different regions</strong> "
                     f"({', '.join(sorted(regions))}), demonstrating a willingness to travel the country "
                     f"and test the game against diverse competition from coast to coast.")
    elif len(regions) >= 3:
        paras.append(f"With tournaments spanning {', '.join(sorted(regions))}, "
                     f"{first} isn't afraid to compete outside the home region — "
                     f"and that exposure to different playing styles only sharpens the game.")

    # === SEEDING RECOGNITION ===
    if len(top_seeds) >= 5:
        paras.append(f"{first} has been <strong>seeded #1 or #2</strong> in {len(top_seeds)} events — "
                     f"recognition by tournament committees that this player consistently ranks among the very best in the draw.")
    elif len(seeded_entries) >= 5:
        paras.append(f"With {len(seeded_entries)} seeded entries across the career, {first} consistently earns "
                     f"the respect of tournament organizers.")

    # === CLOSING ===
    if len(seasons) >= 4 and wins:
        closings = [
            f"With <strong>{len(seasons)} seasons</strong> of competitive experience and {len(wins)} "
            f"title{'s' if len(wins) != 1 else ''}, {first} is a battle-hardened competitor "
            f"whose journey is a testament to dedication, talent, and love for the game.",
            f"Over <strong>{len(seasons)} seasons</strong> and {len(wins)} "
            f"title{'s' if len(wins) != 1 else ''}, {first} has built a legacy that speaks volumes "
            f"about what sustained effort and competitive fire can achieve.",
        ]
        paras.append(rng.choice(closings))
    elif len(seasons) >= 3:
        paras.append(f"With {len(seasons)} seasons of competitive experience, "
                     f"{first} brings <strong>tournament-tested composure</strong> that "
                     f"only comes from years of stepping onto the court against the best.")
    elif len(seasons) >= 2 and total_entries >= 10:
        paras.append(f"Now in the {len(seasons)}{'nd' if len(seasons)==2 else 'rd'} season of competition, "
                     f"{first}'s journey is gathering momentum with every tournament. The future is bright.")

    return "\n".join(f"<p>{p}</p>" for p in paras)


# ── Ordinal helper ───────────────────────────────────────────────────────────
def ordinal(n):
    if 11 <= (n % 100) <= 13: return f"{n}th"
    return f"{n}{['th','st','nd','rd','th'][min(n%10, 4)]}"


# ── Generate roast summary ──────────────────────────────────────────────────
def generate_roast(name, results):
    """Generate a detailed, funny, mean, sarcastic roast of a player."""
    if not results:
        return f"<p>{name} has apparently played badminton. We have no evidence of this.</p>"

    rng = random.Random(hash(name))
    first = name.split()[0]
    results_sorted = sorted(results, key=lambda r: r['dates'].split('/')[0])

    total_entries = len(results)
    all_tournaments = sorted(set(r['tournament'] for r in results))
    num_tournaments = len(all_tournaments)
    wins = [r for r in results if int(r['rank_lo']) == 1]
    finals = [r for r in results if int(r['rank_lo']) == 2]
    semis = [r for r in results if int(r['rank_lo']) in [3, 4]]
    top4 = [r for r in results if int(r['rank_lo']) <= 4]

    tier_results = defaultdict(list)
    tier_wins = defaultdict(list)
    for r in results:
        t = tournament_tier(r['tournament'])
        tier_results[t].append(r)
        if int(r['rank_lo']) == 1: tier_wins[t].append(r)

    s_results = [r for r in results if is_singles(r['event'])]
    d_results = [r for r in results if is_doubles(r['event'])]
    x_results = [r for r in results if is_mixed(r['event'])]
    s_wins = [r for r in wins if is_singles(r['event'])]
    d_wins = [r for r in wins if is_doubles(r['event'])]
    x_wins = [r for r in wins if is_mixed(r['event'])]
    s_finals = [r for r in finals if is_singles(r['event'])]
    d_finals = [r for r in finals if is_doubles(r['event'])]
    x_finals = [r for r in finals if is_mixed(r['event'])]

    age_groups = set()
    for r in results:
        ag = get_age_group(r['event'])
        if ag: age_groups.add(ag)
    ag_sorted = sorted(age_groups, key=lambda x: int(x[1:])) if age_groups else []
    current_ag = None
    for r in reversed(results_sorted):
        current_ag = get_age_group(r['event'])
        if current_ag: break

    tourn_ags = defaultdict(set)
    for r in results:
        ag = get_age_group(r['event'])
        if ag: tourn_ags[r['tournament']].add(ag)
    playing_up_count = sum(1 for ags in tourn_ags.values() if len(ags) >= 2)

    partners = defaultdict(lambda: {'count': 0, 'wins': 0, 'finals': 0, 'best': 999, 'events': []})
    for r in results_sorted:
        if is_singles(r['event']): continue
        p = parse_partner(r['player'], name)
        if p:
            partners[p]['count'] += 1
            rank = int(r['rank_lo'])
            if rank == 1: partners[p]['wins'] += 1
            if rank == 2: partners[p]['finals'] += 1
            if rank < partners[p]['best']: partners[p]['best'] = rank
            partners[p]['events'].append(r)
    num_partners = len(partners)
    top_partner = max(partners.items(), key=lambda x: x[1]['count']) if partners else None

    worst = max(int(r['rank_lo']) for r in results)
    early_exits = [r for r in results if int(r['rank_lo']) >= 9]
    really_bad = [r for r in results if int(r['rank_lo']) >= 17]

    home_state = get_home_state(results, name)
    home_state_name = STATE_NAMES.get(home_state) if home_state else None

    win_rate = len(wins) / total_entries * 100 if total_entries else 0
    podium_rate = len(top4) / total_entries * 100 if total_entries else 0

    seasons_map = defaultdict(list)
    for r in results_sorted:
        seasons_map[get_season(r['dates'].split('/')[0])].append(r)
    season_keys = sorted(seasons_map.keys())

    seeded = [r for r in results if r['seed'] and r['seed'] not in ['', 'WC']]
    seeded_losses = [r for r in seeded if r['seed'].isdigit() and int(r['rank_lo']) > int(r['seed'])]
    seeded_top = [r for r in seeded if r['seed'].isdigit() and int(r['seed']) <= 2]

    recent_season = season_keys[-1] if season_keys else None
    recent_results = seasons_map.get(recent_season, [])
    recent_wins = [r for r in recent_results if int(r['rank_lo']) == 1]
    earlier_seasons_results = [r for s in season_keys[:-1] for r in seasons_map[s]] if len(season_keys) >= 2 else []
    earlier_wins = [r for r in earlier_seasons_results if int(r['rank_lo']) == 1]

    jn_results = tier_results.get('JN', [])
    jn_wins = tier_wins.get('JN', [])
    sel_results = tier_results.get('SEL', [])
    orc_results = tier_results.get('ORC', [])
    orc_wins = tier_wins.get('ORC', [])
    olc_results = tier_results.get('OLC', [])
    olc_wins = tier_wins.get('OLC', [])
    crc_results = tier_results.get('CRC', [])
    crc_wins = tier_wins.get('CRC', [])

    regions = set()
    for t in all_tournaments:
        for region in ['NW', 'NE', 'SoCal', 'NorCal', 'South', 'Midwest']:
            if region in t: regions.add(region); break

    paras = []

    state_from = f"from {home_state_name}" if home_state_name else "from parts unknown"
    ag_note = f" at the {current_ag} level" if current_ag else ""

    jn_champ_events = list(set(r['event'] for r in jn_wins)) if jn_wins else []
    sel_best = min((int(r['rank_lo']) for r in sel_results), default=999)
    jn_best = min((int(r['rank_lo']) for r in jn_results), default=999)

    tourn_entries = defaultdict(list)
    for r in results_sorted:
        tourn_entries[r['tournament']].append(r)
    tourn_wins_ct = {t: sum(1 for r in rs if int(r['rank_lo'])==1) for t, rs in tourn_entries.items()}
    tourn_finals_ct = {t: sum(1 for r in rs if int(r['rank_lo'])==2) for t, rs in tourn_entries.items()}
    tourn_avg = {t: sum(int(r['rank_lo']) for r in rs)/len(rs) for t, rs in tourn_entries.items() if len(rs) >= 2}
    worst_tourn = max(tourn_avg, key=tourn_avg.get) if tourn_avg else None

    first_tourn = results_sorted[0]['tournament']
    first_win_r = next((r for r in results_sorted if int(r['rank_lo'])==1), None)
    multi_final_tourns = {t: ct for t, ct in tourn_finals_ct.items() if ct >= 2}
    worst_doubles = sorted([r for r in d_results + x_results if int(r['rank_lo']) >= 17],
                           key=lambda r: -int(r['rank_lo']))

    # ── PARAGRAPH 1: THE GRAND OPENING ──
    intro = f"Ladies and gentlemen, put your hands together for {name}, {state_from}"
    if current_ag:
        intro += f", currently competing{ag_note}"
    intro += ". "

    if sel_results and sel_best == 1:
        intro += (f"Now, before we get started, we do need to acknowledge that {first} is a U.S. Selection "
                  f"Event champion, which means {first} has literally been chosen to represent this country on "
                  f"the international stage. That is an extraordinary accomplishment and {first} would very much "
                  f"like you to stop reading right here. Unfortunately for {first}, we kept reading — all {total_entries} "
                  f"entries across {num_tournaments} tournaments, to be exact — and what we found behind that one "
                  f"shiny title is a {win_rate:.0f}% career win rate. Let that number sink in. For every time {first} "
                  f"held up a trophy, there were roughly {int(total_entries/max(len(wins),1)) - 1} other times "
                  f"{first} walked out of the gym carrying nothing but a racket bag, a participation wristband, "
                  f"and the quiet dignity of someone pretending it was 'a good learning experience.'")
    elif sel_results:
        intro += (f"This is a player who has competed at the U.S. Selection Event — the single most "
                  f"prestigious tournament in American junior badminton, the one where you play for the right "
                  f"to represent your country — and finished top-{sel_best}. ")
        if jn_wins:
            intro += (f"And yes, {first} IS a Junior National Champion — {', '.join(jn_champ_events)} — which is "
                      f"a legitimate, no-asterisks, put-it-on-the-college-application achievement. We will give "
                      f"that its due respect for about five seconds... okay, time's up. Because behind those "
                      f"headlines is a {total_entries}-entry career across {num_tournaments} tournaments with "
                      f"a {win_rate:.0f}% win rate, which means {total_entries - len(wins)} times — "
                      f"{total_entries - len(wins)}! — {first} went home without a trophy. ")
        else:
            intro += (f"Top-{sel_best} at Selection. So close to the ultimate prize, and yet so far. "
                      f"Across {total_entries} career entries in {num_tournaments} tournaments, {first} has "
                      f"{len(wins)} title{'s' if len(wins)!=1 else ''} — a {win_rate:.0f}% conversion rate. "
                      f"That means for every win, there are about {int(total_entries/max(len(wins),1)) - 1} "
                      f"entries where {first} drove to the gym, paid the fee, warmed up, competed, lost, and "
                      f"drove home. ")
        intro += (f"So buckle in, because we have {total_entries} entries worth of material, and we intend "
                  f"to use every last one of them.")
    elif jn_wins:
        intro += (f"This is a player who has stood at the top of the podium at Junior Nationals — "
                  f"the crown jewel of the American junior badminton calendar — and won {', '.join(jn_champ_events)}. "
                  f"That is a real, verified, indisputable accomplishment, and no one can ever take it away. "
                  f"But here's what they CAN take away: any illusion that the rest of this resume is equally "
                  f"impressive. Because we are looking at {total_entries} career entries across {num_tournaments} "
                  f"tournaments, {len(wins)} total wins, and {total_entries - len(wins)} losses. A {win_rate:.0f}% "
                  f"win rate that suggests the Nationals title was less a coronation and more a cosmic accident "
                  f"that {first} has been unsuccessfully trying to replicate ever since. The story started "
                  f"at {first_tourn}, and it has been a wild, inconsistent, deeply roastable ride from there.")
    elif jn_results:
        intro += (f"This is someone who has been to Junior Nationals — the biggest stage in American junior "
                  f"badminton — and came home with a best finish of top-{jn_best}. Not terrible! Also not a "
                  f"championship. {first} has {total_entries} career entries across {num_tournaments} tournaments "
                  f"and has managed to win {len(wins)} of them — a {win_rate:.0f}% rate that screams 'perennial "
                  f"contender who cannot close.' We are sure the 'I almost had it at Nationals' story absolutely "
                  f"kills at family dinners, right between the appetizer and that look of quiet disappointment "
                  f"from the parent who drove nine hours to watch two matches.")
    elif orc_wins:
        intro += (f"An Open Regional Championship titlist with {len(orc_wins)} ORC "
                  f"title{'s' if len(orc_wins)!=1 else ''}, which sounds very official — and it is, ORCs are "
                  f"the real deal. But let's zoom out: that's {len(orc_wins)} wins out of {len(orc_results)} ORC entries, "
                  f"and an overall career of {len(wins)}-for-{total_entries} ({win_rate:.0f}%). Regional royalty, "
                  f"national afterthought. A big deal on the local circuit, a footnote everywhere else. "
                  f"Let's dig in.")
    elif len(wins) >= 5:
        local_w = len(olc_wins) + len(crc_wins)
        intro += (f"A player with {len(wins)} career titles, which sounds impressive until you learn that "
                  f"{local_w} of them came at local events where the draw is thinner than gas station coffee and "
                  f"the toughest opponent is someone's cousin who picked up a racket six months ago. A "
                  f"{win_rate:.0f}% win rate across {total_entries} entries — big fish, very small pond, "
                  f"possibly a puddle. But {first} keeps entering, keeps competing, and keeps providing "
                  f"us with material. For that, we are grateful.")
    elif not wins and total_entries >= 10:
        intro += (f"A player who has entered {total_entries} events across {num_tournaments} tournaments "
                  f"and has won exactly zero of them. Not one. We checked twice. This is not a typo, and it "
                  f"is not bad luck — it is a {total_entries}-event streak that statisticians would describe as "
                  f"'impressively consistent at not winning.' {first}'s trophy case is so empty it echoes. "
                  f"And yet, {first} keeps coming back, which is either the most inspiring thing we have ever "
                  f"seen or a cry for help. We genuinely cannot tell.")
    elif not wins:
        intro += (f"A player with {total_entries} career entr{'y' if total_entries==1 else 'ies'} and zero wins. "
                  f"The journey of a thousand losses begins with a single entry form, and {first} is right "
                  f"on schedule. It all started at {first_tourn}, and so far, the only thing {first} has "
                  f"collected is experience — which is what people say when they have nothing else to show for it.")
    else:
        intro += (f"A player with {len(wins)} win{'s' if len(wins)!=1 else ''} across {total_entries} entries "
                  f"in {num_tournaments} tournaments. That is a {win_rate:.0f}% conversion rate, which means "
                  f"roughly {10 - int(win_rate/10)} out of every 10 times {first} shows up to a tournament, "
                  f"{first} pays the entry fee, laces up the shoes, does the warm-up jog, stretches the "
                  f"hamstrings, steps on court... and then drives home with absolutely nothing to show for it "
                  f"except sore legs and a lighter wallet.")
    paras.append(intro)

    # ── PARAGRAPH 2: ORIGIN STORY & CAREER ARC ──
    arc = f"The {first} saga began at {first_tourn}"
    first_results = tourn_entries[first_tourn]
    first_best = min(int(r['rank_lo']) for r in first_results)
    first_count = len(first_results)
    if first_win_r and first_win_r['tournament'] == first_tourn:
        arc += (f", where {first} burst onto the scene with a title in {first_win_r['event']} — "
                f"a debut that promised great things. And to be fair, {first} has delivered on some of those "
                f"promises: {len(wins)} total titles is nothing to sneeze at. But the gap between what {first} "
                f"promised and what {first} has delivered is wide enough to park a minivan in.")
    elif first_win_r:
        arc += (f" with {first_count} entries and a best finish of {ordinal(first_best)}. "
                f"The first title would not come until {first_win_r['tournament']} in {first_win_r['event']}, "
                f"and you could almost hear the collective sigh of relief from {first}'s family, who had been "
                f"patiently attending tournaments and pretending it was 'all about the experience.'")
    else:
        arc += (f" with {first_count} entries and a best of {ordinal(first_best)}, and somehow the winning "
                f"has not started yet — {len(seasons_map)} seasons later.")

    if len(season_keys) >= 2:
        season_win_rates = {}
        for s in season_keys:
            sr = seasons_map[s]
            sw = sum(1 for r in sr if int(r['rank_lo'])==1)
            season_win_rates[s] = (sw, len(sr))
        best_season = max(season_keys, key=lambda s: season_win_rates[s][0])
        best_sw, best_se = season_win_rates[best_season]
        if best_sw > 0:
            recent_sw, recent_se = season_win_rates[recent_season]
            if recent_season != best_season and best_sw > recent_sw:
                arc += (f" The peak came during the {best_season} season — {best_sw} "
                        f"title{'s' if best_sw!=1 else ''} in {best_se} entries — a stretch where {first} "
                        f"actually looked like the player everyone hoped for. ")
                if recent_sw == 0:
                    arc += (f"Fast forward to this season and {first} is 0-for-{recent_se}. "
                            f"The glory days are not just over — they are actively running in the other direction.")
                elif recent_sw < best_sw:
                    arc += (f"This season? {recent_sw} win{'s' if recent_sw!=1 else ''} in {recent_se} entries. "
                            f"The trajectory is... let's call it 'humbling.'")
            elif recent_season == best_season and best_sw >= 2:
                arc += (f" This {recent_season} season has actually been the best yet — {best_sw} "
                        f"title{'s' if best_sw!=1 else ''} in {best_se} entries — which really tells you "
                        f"everything about how low the bar was before.")
    paras.append(arc)

    # ── PARAGRAPH 3: THE FINALS PROBLEM ──
    if len(finals) >= 3 or (len(finals) >= 2 and not wins):
        p3 = (f"But nothing — absolutely nothing — defines the {first} experience quite like the finals record. "
              f"Let us walk you through this, because the numbers alone do not do it justice. ")
        if len(finals) >= 3:
            p3 += (f"{first} has reached {len(finals)} championship matches across this career. "
                   f"That is {len(finals)} times standing one single match away from a title — the bracket won, "
                   f"the semifinal opponent dispatched, the crowd watching, the trophy right there — and "
                   f"{len(finals)} times walking away empty-handed. ")
            if multi_final_tourns:
                worst_t = max(multi_final_tourns, key=multi_final_tourns.get)
                worst_ct = multi_final_tourns[worst_t]
                worst_t_entries = tourn_entries[worst_t]
                worst_t_events = [r['event'] for r in worst_t_entries if int(r['rank_lo'])==2]
                p3 += (f"Take {worst_t}, where {first} entered {len(worst_t_entries)} events and came away with "
                       f"{worst_ct} runner-up finishes ({', '.join(worst_t_events)}). {worst_ct} chances at "
                       f"gold, {worst_ct} silver medals. That is not bad luck — that is an IDENTITY. ")
            if s_finals and (d_finals or x_finals):
                p3 += (f"It happens in singles ({len(s_finals)} finals losses), and it happens in doubles and "
                       f"mixed ({len(d_finals) + len(x_finals)} more). This is not a discipline-specific problem — "
                       f"this is a spiritual condition. ")
            if wins:
                p3 += (f"Now yes, {first} does own {len(wins)} actual title{'s' if len(wins)!=1 else ''}, so it "
                       f"is not like {first} has never won anything. But {len(finals)} finals losses versus "
                       f"{len(wins)} wins means {first} is literally more likely to choke in a championship match "
                       f"than to win one. The clutch gene is not missing — it's just on an extremely unreliable "
                       f"part-time schedule, like a substitute teacher who shows up whenever they feel like it.")
            else:
                p3 += (f"And remember: {first} has ZERO titles. None. {len(finals)} times in the final, "
                       f"zero trophies to show for it. This is the most committed bridesmaid in the history "
                       f"of junior badminton.")
        else:
            finals_tourns = list(set(f['tournament'] for f in finals))
            p3 += (f"{first} has reached the finals {len(finals)} time{'s' if len(finals)>1 else ''} — "
                   f"at {', '.join(finals_tourns[:3])} — and lost every time. Winning every match in a "
                   f"tournament except the one that actually matters takes a special kind of talent, "
                   f"and {first} has it in spades.")
        paras.append(p3)
    elif len(semis) >= 4 and len(wins) <= 2:
        paras.append(
            f"If there were a trophy for semifinal exits, {first} would have a dynasty that would make "
            f"the New England Patriots jealous. {len(semis)} times {first} has fought to the final four — "
            f"the point where the tournament is supposed to get exciting — and {len(semis)} times {first} "
            f"has been sent home before the championship match even started. It is like having a GPS "
            f"programmed to shut off one turn before the destination, every single time. The semifinals should "
            f"honestly be renamed in {first}'s honor, because nobody has spent more time there without "
            f"advancing.")

    # ── PARAGRAPH 4: DISCIPLINE & DOUBLES DEEP-DIVE ──
    p4_parts = []
    has_all_three = s_results and d_results and x_results
    if has_all_three:
        p4 = (f"Let us talk about the discipline split, because this is where the story gets interesting. "
              f"{first} plays singles, doubles, AND mixed doubles, which on paper looks like the résumé of a "
              f"well-rounded, versatile athlete. On closer inspection, it looks more like the résumé of someone "
              f"who keeps trying different formats hoping one of them will work. ")
        if not s_wins and (d_wins or x_wins):
            doubles_w = len(d_wins) + len(x_wins)
            s_best = min(int(r['rank_lo']) for r in s_results)
            p4 += (f"In singles — the purest test of individual skill, where there is nowhere to hide and no "
                   f"one else to blame — {first} is 0-for-{len(s_results)}. Zero titles in {len(s_results)} "
                   f"tries. The best singles result is a {ordinal(s_best)}-place finish, which is the kind of "
                   f"thing you technically cannot put on a highlight reel. But here is the twist: put a partner "
                   f"on the court alongside {first} and suddenly the wins start appearing — {doubles_w} titles "
                   f"in doubles and mixed. The data is screaming a very clear message: {first} needs help. "
                   f"Alone? Winless. With a teammate? A champion. There is probably a metaphor about teamwork "
                   f"in there somewhere, but honestly it just looks like someone who cannot get the job done solo.")
        elif s_wins and not d_wins and not x_wins:
            p4 += (f"All {len(s_wins)} title{'s' if len(s_wins)!=1 else ''} came in singles — the discipline "
                   f"where nobody else can mess things up. In doubles? Zero titles. In mixed? Also zero. "
                   f"Either {first} is a lone wolf who thrives in isolation, or — and this is our working "
                   f"theory — nobody wants to be the partner who has to explain the loss at dinner.")
        elif not s_wins and not d_wins and not x_wins:
            p4 += (f"Three disciplines, {total_entries} entries, zero titles in any format. That is not "
                   f"versatility — that is just expanding the portfolio of failure across multiple asset classes. "
                   f"Diversification does not help when every investment returns zero.")
        else:
            p4 += (f"The breakdown: {len(s_wins)} singles, {len(d_wins)} doubles, {len(x_wins)} mixed "
                   f"title{'s' if len(x_wins)!=1 else ''}. Jack of all trades and a master of — well, let "
                   f"us be generous and leave that sentence unfinished. The point is, {first} can technically "
                   f"win in any format, just not often enough for anyone to be truly impressed.")
        p4_parts.append(p4)
    elif s_results and not d_results and not x_results:
        p4_parts.append(
            f"{first} is a singles purist — no doubles, no mixed, just one person on each side of the net "
            f"and nowhere to hide. Either nobody wants to be {first}'s partner (and honestly, looking at these "
            f"numbers, who could blame them), or {first} is the kind of competitor who refuses to share credit. "
            f"Admirable? Maybe. Lonely? Definitely.")
    elif not s_results and (d_results or x_results):
        p4_parts.append(
            f"{first} plays exclusively doubles formats — not a single singles entry to be found. There is "
            f"something very telling about a player who never steps on court alone. You cannot fail a test "
            f"by yourself if you always bring a study buddy. Smart, perhaps, but not exactly a vote of "
            f"confidence in one's own abilities.")

    if num_partners >= 5 or (top_partner and top_partner[1]['count'] >= 5):
        partner_p = ""
        if num_partners >= 8:
            partner_p = (f"And then there are the partners — {num_partners} of them, to be precise. "
                         f"{first} has burned through doubles partners the way some people burn through Netflix "
                         f"shows: binge, lose interest, move on. The revolving door spins so fast it is a miracle "
                         f"anyone still answers {first}'s texts. ")
        elif num_partners >= 5:
            partner_p = (f"On the doubles front, {first} has cycled through {num_partners} different partners, "
                         f"which is either a sign of someone constantly searching for the perfect fit or — more "
                         f"likely — a sign that the partners keep finding excuses to be 'unavailable.' ")
        if top_partner:
            tp_name, tp_info = top_partner
            if tp_info['count'] >= 5 and tp_info['wins'] == 0:
                partner_p += (f"The longest-running partnership is with {tp_name}: {tp_info['count']} events "
                              f"together, zero titles. Let that marinate. {tp_info['count']} tournaments of "
                              f"shared warm-ups, shared strategies, shared hotel lobbies — and shared losses. "
                              f"That is not a doubles partnership; that is a mutual support group. "
                              f"We hope {tp_name} has a good therapist.")
            elif tp_info['count'] >= 5 and tp_info['wins'] >= 3:
                partner_p += (f"The most successful partnership is with {tp_name} — {tp_info['count']} events, "
                              f"{tp_info['wins']} titles — and honestly, {tp_name} deserves hazard pay for "
                              f"carrying this doubles career on their back. Someone send {tp_name} "
                              f"a thank-you card, a gift basket, and maybe a chiropractor referral for all that heavy lifting.")
            elif tp_info['count'] >= 3:
                partner_p += (f"The go-to partner is {tp_name} ({tp_info['count']} events, {tp_info['wins']} "
                              f"win{'s' if tp_info['wins']!=1 else ''}), which "
                              f"{'is the definition of diminishing returns' if not tp_info['wins'] else 'is not exactly setting the world on fire'}.")
        if worst_doubles:
            wd = worst_doubles[0]
            wd_partner = parse_partner(wd['player'], name)
            partner_p += (f" The doubles lowlight? A round-of-{int(wd['rank_lo'])} exit at "
                          f"{wd['tournament']} in {wd['event']}"
                          f"{' — we hope ' + wd_partner + ' has emotionally recovered' if wd_partner else ''}.")
        if partner_p:
            p4_parts.append(partner_p)
    if p4_parts:
        paras.append(" ".join(p4_parts))

    # ── PARAGRAPH 5: BIG STAGE & SEEDING ──
    p5_parts = []
    local_w = len(olc_wins) + len(crc_wins)
    big_w = len(orc_wins) + len(jn_wins) + len(tier_wins.get('SEL', []))
    if local_w > 0 and big_w == 0 and orc_results:
        p5_parts.append(
            f"Now, about the quality of those wins. Every single one of {first}'s {local_w} "
            f"title{'s' if local_w!=1 else ''} came at local events — OLCs and CRCs — where the field is "
            f"small, the competition is friendly, and the biggest obstacle is finding parking. At the ORC "
            f"level and above, where the elite show up and the brackets get serious? Zero titles. "
            f"It is the competitive equivalent of being the tallest kid in kindergarten and thinking you "
            f"are ready for the NBA.")
    elif local_w > big_w and big_w > 0 and local_w >= 3:
        p5_parts.append(
            f"Of {first}'s {len(wins)} career titles, {local_w} came at local events versus {big_w} at "
            f"ORCs or higher. That ratio tells you everything: {first} feasts when the field is weak and "
            f"struggles when the competition shows up. The résumé is padded the way a freshman pads a "
            f"college application with 'extracurricular activities' that were really just sitting in a room.")

    if sel_results and not tier_wins.get('SEL') and len(sel_results) >= 2:
        sel_worst = max(int(r['rank_lo']) for r in sel_results)
        sel_entries = len(sel_results)
        p5_parts.append(
            f"At the Selection Event — where the stakes are as high as they get in American junior badminton — "
            f"{first} entered {sel_entries} events with results ranging from top-{sel_best} to a humbling "
            f"round-of-{sel_worst}. The Selection committee looked at {first}'s record and saw enough talent "
            f"to deserve an invitation. The bracket looked at {first} and said 'nah.'")
    if jn_results and not jn_wins:
        jn_entries_ct = len(jn_results)
        jn_finals_ct = sum(1 for r in jn_results if int(r['rank_lo'])==2)
        if jn_finals_ct >= 2:
            p5_parts.append(
                f"Junior Nationals has been particularly cruel: {jn_entries_ct} entries, {jn_finals_ct} finals "
                f"appearances, and zero titles. {first} has stood on the biggest stage in American junior "
                f"badminton, one match from the most important title in the sport, and come up short "
                f"{jn_finals_ct} times. That is the kind of heartbreak that builds character — or "
                f"destroys it. Time will tell.")
        elif jn_finals_ct == 1:
            p5_parts.append(
                f"At Junior Nationals — the Super Bowl of this sport — {first} has competed {jn_entries_ct} "
                f"time{'s' if jn_entries_ct!=1 else ''}, reaching the final once and coming away without the title. "
                f"So close to being a national champion, and yet so definitively not one.")
        elif jn_best <= 4:
            p5_parts.append(
                f"Junior Nationals has seen {first} {jn_entries_ct} time{'s' if jn_entries_ct!=1 else ''}, with a "
                f"best of top-{jn_best}. Close enough to the podium to feel the confetti, not close enough "
                f"to actually catch any.")
        else:
            p5_parts.append(
                f"At Junior Nationals, {first} has shown up {jn_entries_ct} time{'s' if jn_entries_ct!=1 else ''} "
                f"with a best of top-{jn_best}. "
                f"{'Respectable, but nobody remembers who finished top-' + str(jn_best) + '.' if jn_best <= 12 else 'Nobody is making a documentary about this.'}")
    if len(seeded_losses) >= 3:
        worst_upset = max(seeded_losses, key=lambda r: int(r['rank_lo']) - int(r['seed']))
        p5_parts.append(
            f"Then there is the seeding situation. {first} has been seeded in {len(seeded)} events and "
            f"underperformed the seeding {len(seeded_losses)} times. A seed is supposed to be a badge of "
            f"honor — tournament committees studying the field, running the numbers, and saying 'this player "
            f"belongs at the top of the bracket.' {first} takes that badge and promptly sets it on fire. "
            f"The worst offense: seeded #{worst_upset['seed']} at {worst_upset['tournament']} in "
            f"{worst_upset['event']}, and finishing {ordinal(int(worst_upset['rank_lo']))}. That is a "
            f"seeded player losing to multiple unseeded opponents. The committee believed in {first}. "
            f"The evidence suggests they should not have.")
    elif len(seeded_top) >= 3:
        top_losses = [r for r in seeded_top if int(r['rank_lo']) > 2]
        if top_losses:
            tl = top_losses[0]
            p5_parts.append(
                f"Tournament committees have handed {first} a #1 or #2 seed {len(seeded_top)} times, and "
                f"{first} has failed to live up to it in {len(top_losses)} of them — including at "
                f"{tl['tournament']} in {tl['event']}, where {first} was seeded #{tl['seed']} and "
                f"finished {ordinal(int(tl['rank_lo']))}. Being the top seed and still losing is like "
                f"being the teacher's pet and still failing the exam.")
    if p5_parts:
        paras.append(" ".join(p5_parts))

    # ── PARAGRAPH 6: ROAD WARRIOR & PLAYING UP ──
    p6_parts = []
    if playing_up_count >= 3 and len(ag_sorted) >= 3:
        up_results = [r for r in results if get_age_group(r['event']) and get_age_group(r['event']) != ag_sorted[0]]
        up_wins = [r for r in up_results if int(r['rank_lo']) == 1]
        p6_parts.append(
            f"One thing nobody can accuse {first} of is playing it safe. {first} has entered older age groups "
            f"at {playing_up_count} different tournaments, spanning {', '.join(ag_sorted)} — which means {first} "
            f"has voluntarily walked into brackets full of bigger, older, more experienced players and said "
            f"'yes, I would like to compete against these people who have been alive longer than me.' "
            f"{'And incredibly, ' + str(len(up_wins)) + ' of those playing-up attempts ended in a title, which takes the insanity from pure to impressive.' if up_wins else 'The results in those older brackets have been... character-building.'} "
            f"There is a fine line between 'fearless competitor who seeks out the toughest challenges' and "
            f"'person who genuinely enjoys getting bodied by bigger kids,' and {first} has built a permanent "
            f"residence on that line.")
    elif playing_up_count >= 1:
        p6_parts.append(
            f"{first} has also played up into older age groups at {playing_up_count} "
            f"tournament{'s' if playing_up_count>1 else ''}, which is the badminton equivalent of a sophomore "
            f"crashing the senior prom — bold, admirable, and almost always ending in tears.")
    if len(regions) >= 4:
        far_bad = None
        far_results = [r for r in results if int(r['rank_lo']) >= 17]
        if far_results:
            far_bad = max(far_results, key=lambda r: int(r['rank_lo']))
        p6_parts.append(
            f"And let us talk about the travel schedule, because {first} is not just losing locally — {first} "
            f"is losing NATIONALLY. Tournaments across {len(regions)} regions ({', '.join(sorted(regions))}) "
            f"means airplane tickets, hotel rooms, rental cars, tournament entry fees, and the kind of family "
            f"logistics that require a spreadsheet and a prayer. All in pursuit of a {win_rate:.0f}% win rate. "
            f"Most families travel cross-country to visit the Grand Canyon or Disney World. The {name.split()[-1]} "
            f"family travels cross-country so {first} can lose at badminton in exciting new zip codes."
            + (f" The crown jewel of the travel schedule? A round-of-{int(far_bad['rank_lo'])} finish at "
               f"{far_bad['tournament']}. Hope the hotel at least had a pool." if far_bad else ""))
    elif len(regions) >= 2:
        p6_parts.append(
            f"{first} has competed across {len(regions)} different regions, which means the losing is not "
            f"confined to one part of the country — it is a nationally distributed phenomenon.")
    if p6_parts:
        paras.append(" ".join(p6_parts))

    # ── PARAGRAPH 7: LOWLIGHTS ──
    if really_bad or len(early_exits) >= 5:
        p7 = f"We would be doing a disservice to the art of the roast if we did not address the lowlights. "
        if really_bad:
            worst_result = max(really_bad, key=lambda r: int(r['rank_lo']))
            worst_rank = int(worst_result['rank_lo'])
            second_worst = sorted(really_bad, key=lambda r: -int(r['rank_lo']))
            p7 += (f"{first} has {len(really_bad)} career results of round-of-17 or worse — tournaments "
                   f"where {first} showed up, played maybe one match, lost, and went home before the gym even "
                   f"got properly warm. The absolute rock bottom was a {ordinal(worst_rank)}-place finish at "
                   f"{worst_result['tournament']} in {worst_result['event']}, which means {first} traveled to "
                   f"a tournament, registered, warmed up, stepped on court, and was eliminated so quickly that "
                   f"the ink on the draw sheet was still wet. ")
            if len(second_worst) >= 2 and int(second_worst[1]['rank_lo']) >= 17:
                sw = second_worst[1]
                p7 += (f"And it was not a one-time thing — there was also a round-of-{int(sw['rank_lo'])} at "
                       f"{sw['tournament']} in {sw['event']}. A pattern, not a blip. ")
            if worst_tourn and tourn_avg[worst_tourn] >= 15:
                wt_results = tourn_entries[worst_tourn]
                wt_best = min(int(r['rank_lo']) for r in wt_results)
                wt_worst = max(int(r['rank_lo']) for r in wt_results)
                p7 += (f"The single worst tournament experience was {worst_tourn}, where {first} entered "
                       f"{len(wt_results)} events with results ranging from {ordinal(wt_best)} to "
                       f"{ordinal(wt_worst)}. That is an average placement of {ordinal(int(tourn_avg[worst_tourn]))}, "
                       f"which is a polite way of saying {first} paid full price to get absolutely demolished.")
        if len(early_exits) >= 5 and not really_bad:
            p7 += (f"{first} has {len(early_exits)} career results outside the top 8, which means {first} "
                   f"has spent a remarkable amount of time as a spectator at tournaments {first} entered as "
                   f"a competitor. Watching other players contest the quarterfinals from the bleachers while "
                   f"eating a granola bar and pretending to check a phone is not a vibe, but it is one {first} "
                   f"knows intimately.")
        paras.append(p7)

    # ── PARAGRAPH 8: THE CLOSER ──
    if len(seasons_map) >= 4 and not wins:
        closer = (
            f"So here we are: {len(seasons_map)} seasons, {total_entries} entries, and not a single title to show "
            f"for any of it. Most people would have taken a long, hard look in the mirror by now. Most people "
            f"would have considered tennis, or chess, or literally any hobby with a higher return on investment "
            f"than junior badminton. But not {first}. {first} just fills out another entry form, packs the "
            f"racket bag, and drives to the next tournament with the unshakable optimism of someone who has "
            f"never read their own statistics. The definition of insanity is doing the same thing over and over "
            f"and expecting different results — and {first} has turned that into a multi-year lifestyle. "
            f"But you know what? The sport needs people like {first}. Every bracket needs a first-round opponent. "
            f"Every tournament needs entry fees. And every champion needs someone to beat on the way to the title. "
            f"So from the bottom of our hearts, {first}: thank you for your service. We mean that. Mostly.")
    elif len(seasons_map) >= 2 and wins:
        closer = (
            f"So where does this leave us? {len(seasons_map)} seasons deep, {len(wins)} "
            f"title{'s' if len(wins)!=1 else ''} to the name, {total_entries} entries, "
            f"and {total_entries - len(wins)} losses. If you squint at the highlights — the "
            f"{'national title' if jn_wins else 'Selection Event appearance' if sel_results else 'ORC victories' if orc_wins else 'local titles'}"
            f", the big wins, the moments of genuine brilliance — {first} looks like a player on the rise. "
            f"But we did not squint. We pulled up every single entry, every draw, every result, and what we "
            f"found is a player who {'chokes in finals like it is a hobby' if len(finals) >= 3 else 'has a complicated relationship with winning'}, "
            f"{'cannot win a singles match to save their life' if s_results and not s_wins else 'treats seeds like suggestions' if len(seeded_losses) >= 3 else 'keeps searching for the right doubles partner like a bad dating app' if num_partners >= 8 else 'is still figuring it out'}, "
            f"and travels the country paying entry fees with the enthusiasm of someone who truly believes the "
            f"next tournament will be different. And maybe it will be. But probably not. The data is not on "
            f"{first}'s side, but the human spirit is a powerful thing, and {first} has enough of it to "
            f"power a small city. So keep swinging, {first}. The shuttle tube industry thanks you. "
            f"The tournament organizers thank you. The opponents who padded their records against you "
            f"thank you most of all. We will be watching.")
    elif len(seasons_map) >= 2:
        closer = (
            f"Season after season, {first} keeps coming back — packing the bag, paying the fees, "
            f"driving to gyms in cities {first} has never been to, and doing it all over again. Some people "
            f"call that grit. Some people call that stubbornness. Some people call that a refusal to read "
            f"a spreadsheet. Whatever it is, the junior circuit would genuinely not be the same without "
            f"{first}, and we mean that in every possible interpretation of the sentence. Keep swinging, "
            f"{first}. We will be here, taking notes.")
    else:
        closer = (
            f"{first} is just getting started on the circuit, which means there is still time. Time to "
            f"turn this around, time to find a groove, time to become the player the entry form says "
            f"{first} wants to be. Or — and this is statistically more likely — time to accumulate a much "
            f"longer and more detailed record of losing, which will make for an even better roast in two "
            f"years. Either way, we are invested now. Welcome to junior badminton, {first}, where the "
            f"shuttles are fast, the parents are intense, and the entry fees never stop. We will be watching.")
    paras.append(closer)

    return "\n".join(f"<p>{p}</p>" for p in paras)


# ── Build player data for JSON ────────────────────────────────────────────────
def build_player_data(name, results):
    results_sorted = sorted(results, key=lambda r: r['dates'].split('/')[0])
    seasons = defaultdict(list)
    for r in results_sorted:
        seasons[get_season(r['dates'].split('/')[0])].append(r)

    summary = generate_summary(name, results)
    roast = generate_roast(name, results)

    month_names = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                   'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

    wins = sum(1 for r in results if int(r['rank_lo']) == 1)
    finals_count = sum(1 for r in results if int(r['rank_lo']) == 2)
    semis_count = sum(1 for r in results if int(r['rank_lo']) in [3, 4])
    tournaments = len(set(r['tournament'] for r in results))

    # Build season rows — REVERSE ORDER (most recent first)
    season_data = {}
    for season in sorted(seasons.keys(), reverse=True):
        rows = []
        for r in seasons[season]:
            start = r['dates'].split('/')[0]
            y, m, d = start.split('-')
            date_str = f"{month_names[int(m)]} {y}"
            partner = parse_partner(r['player'], name) or None
            rank_str = format_rank(r['rank_lo'], r['rank_hi'])
            seed = r['seed'] if r['seed'] else ''
            rank_lo = int(r['rank_lo'])

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
        'roast': roast,
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

# ── Save player slug mapping ─────────────────────────────────────────────────
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
.roast-disclaimer { background: #2d2d2d; border: 1px solid #ff4444; border-radius: 8px; padding: 16px 20px; margin: 16px 0; font-size: 13px; color: #ffcccc; line-height: 1.6; }
.roast-disclaimer strong { color: #ff6666; }
.roast-mode .header { background: linear-gradient(135deg, #1a1a2e, #16213e); }
.roast-mode .summary { background: #1a1a2e; color: #e0e0e0; border: 1px solid #333; }
.roast-mode .summary strong { color: #ff8888; }
.roast-mode body { background: #0f0f1a; }
.roast-mode .stat-box { background: #1a1a2e; color: #ccc; border: 1px solid #333; }
.roast-mode .stat-box .num { color: #ff6666; }
.roast-mode .stat-box.gold .num { color: #ff6666; }
.roast-mode .stat-box .label { color: #888; }
.roast-mode table { background: #1a1a2e; border: 1px solid #333; }
.roast-mode th { background: #16213e; }
.roast-mode td { border-bottom-color: #2a2a3e; color: #ccc; }
.roast-mode tr:hover { background: #22223a; }
.roast-mode tr.winner { background: #2a2020; }
.roast-mode tr.winner:hover { background: #332828; }
.roast-mode .season-header { color: #ff8888; border-bottom-color: #ff6666; }
.roast-mode a { color: #6688cc; }
.roast-badge { display: inline-block; background: #ff4444; color: white; font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 4px; margin-left: 8px; vertical-align: middle; letter-spacing: 0.5px; }
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
  const isRoast = params.has('roast');
  if (!slug) { document.getElementById('loading').textContent = 'No player specified.'; return; }
  if (isRoast) document.body.classList.add('roast-mode');

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
    document.title = (isRoast ? '\ud83d\udd25 ' : '') + p.name + ' \u2014 USA Badminton Junior Results';
    document.getElementById('playerName').innerHTML = esc(p.name) + (isRoast ? '<span class="roast-badge">\ud83d\udd25 ROAST MODE</span>' : '');
    document.getElementById('playerSubtitle').textContent = p.stats.entries + ' results across ' + p.stats.tournaments + ' tournaments';

    const s = p.stats;
    let html = '<div class="stats-bar">' +
      '<div class="stat-box gold"><div class="num">' + s.wins + '</div><div class="label">Titles</div></div>' +
      '<div class="stat-box"><div class="num">' + s.finals + '</div><div class="label">Finals</div></div>' +
      '<div class="stat-box"><div class="num">' + s.semis + '</div><div class="label">Semifinals</div></div>' +
      '<div class="stat-box"><div class="num">' + s.tournaments + '</div><div class="label">Tournaments</div></div>' +
      '<div class="stat-box"><div class="num">' + s.seasons + '</div><div class="label">Seasons</div></div>' +
      '</div>';

    if (isRoast) {
      html += '<div class="roast-disclaimer"><strong>\ud83d\udd25 ROAST MODE</strong> \u2014 This is a comedic roast generated for entertainment purposes only. It is intentionally mean, sarcastic, and exaggerated. None of it should be taken seriously. Every player on this circuit works incredibly hard, and we respect them all. If you want the real summary, <a href="player.html?id=' + slug + '" style="color:#6688ff">click here</a>.</div>';
      html += '<div class="summary">' + (p.roast || p.summary) + '</div>';
    } else {
      html += '<div class="summary">' + p.summary + '</div>';
      html += '<div class="disclaimer">\u26a0 This summary is AI-generated based on tournament draw data. Results may contain errors due to name parsing in doubles events, age group splits across venues, or data entry variations. Always verify with official USA Badminton records.</div>';
    }

    // Seasons are already in reverse order from the JSON
    const seasonKeys = Object.keys(p.seasons).sort().reverse();
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
