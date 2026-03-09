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
    return re.sub(r'\s*\[[\w/]+\]', '', raw).strip()

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
for r in all_results:
    raw = r['player']
    raw_clean = clean_name(raw)
    for name in unique_players:
        if name in raw_clean:
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

    # Partners
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
        for p, info in top_partners[:3]:
            count = info['count']
            p_wins = info['wins']
            p_best = info['best']
            event_types = "/".join(sorted(info['events']))
            if p_wins >= 2:
                partner_paras.append(f"<strong>{p}</strong> — {count} events in {event_types}, "
                                    f"producing {p_wins} titles together")
            elif p_wins == 1:
                partner_paras.append(f"<strong>{p}</strong> — {count} events, 1 title together in {event_types}")
            elif count >= 4:
                best_str = f", best: #{p_best}" if p_best <= 8 else ""
                partner_paras.append(f"<strong>{p}</strong> — a trusted {event_types} partner ({count} events{best_str})")
            elif count >= 2 and p_best <= 4:
                partner_paras.append(f"<strong>{p}</strong> — {count} events in {event_types}, best: #{p_best}")

        if partner_paras:
            if num_partners >= 5:
                intro = rng.choice([
                    f"{first} has shown remarkable <strong>doubles adaptability</strong>, partnering with {num_partners} different players:",
                    f"With {num_partners} different doubles partners across the career, {first} adapts to anyone:",
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


# ── Build player data for JSON ────────────────────────────────────────────────
def build_player_data(name, results):
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
