"""Generate roast/sarcastic summaries for a few test players."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import csv, os, re, random
from collections import defaultdict, Counter

DRAWS_DIR = "data/draws"

# Reuse helpers from gen_player_pages
def clean_name(raw):
    return re.sub(r'\s*\[[\w/]+\]', '', raw).strip()

def get_season(date_str):
    year, month = int(date_str[:4]), int(date_str[5:7])
    return f"{year}-{year+1}" if month >= 8 else f"{year-1}-{year}"

def tournament_tier(name):
    if 'Selection' in name: return 'SEL'
    if 'National' in name: return 'JN'
    if 'ORC' in name: return 'ORC'
    if 'CRC' in name: return 'CRC'
    return 'OLC'

def is_singles(e): return e.startswith('BS') or e.startswith('GS') or 'Singles' in e
def is_doubles(e): return e.startswith('BD') or e.startswith('GD')
def is_mixed(e): return e.startswith('XD') or 'Mixed' in e
def get_age_group(e):
    for ag in ['U11','U13','U15','U17','U19']:
        if ag in e: return ag
    return None

def parse_partner(player_field, player_name):
    clean = clean_name(player_field)
    if clean == player_name: return None
    if clean.startswith(player_name): return clean[len(player_name):]
    if clean.endswith(player_name): return clean[:-len(player_name)]
    return clean.replace(player_name, '').strip() or None

def ordinal(n):
    if 11 <= (n % 100) <= 13: return f"{n}th"
    return f"{n}{['th','st','nd','rd','th'][min(n%10, 4)]}"

def get_home_state(results, player_name):
    states = []
    for r in results:
        if is_singles(r['event']) and r.get('state') and len(r['state']) == 2:
            states.append(r['state'])
    return Counter(states).most_common(1)[0][0] if states else None

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

# ── Load data ────────────────────────────────────────────────────────────────
print("Loading results...")
all_results = []
for fn in sorted(os.listdir(DRAWS_DIR)):
    if not fn.endswith('.csv'): continue
    with open(os.path.join(DRAWS_DIR, fn), encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if row['player']:
                all_results.append(row)

player_names = set()
for r in all_results:
    if is_singles(r['event']):
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

player_results = defaultdict(list)
for r in all_results:
    raw_clean = clean_name(r['player'])
    for name in unique_players:
        if name in raw_clean:
            player_results[name].append(r)


# ── ROAST SUMMARY ────────────────────────────────────────────────────────────
def generate_roast(name, results):
    """Generate a detailed, funny, mean, sarcastic roast of a player based on their stats."""
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

    # Age groups
    age_groups = set()
    for r in results:
        ag = get_age_group(r['event'])
        if ag: age_groups.add(ag)
    ag_sorted = sorted(age_groups, key=lambda x: int(x[1:])) if age_groups else []
    current_ag = None
    for r in reversed(results_sorted):
        current_ag = get_age_group(r['event'])
        if current_ag: break

    # Playing up detection
    tourn_ags = defaultdict(set)
    for r in results:
        ag = get_age_group(r['event'])
        if ag: tourn_ags[r['tournament']].add(ag)
    playing_up_count = sum(1 for ags in tourn_ags.values() if len(ags) >= 2)

    # Partners with full details
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

    # Worst results
    worst = max(int(r['rank_lo']) for r in results)
    early_exits = [r for r in results if int(r['rank_lo']) >= 9]
    really_bad = [r for r in results if int(r['rank_lo']) >= 17]

    home_state = get_home_state(results, name)
    home_state_name = STATE_NAMES.get(home_state) if home_state else None

    win_rate = len(wins) / total_entries * 100 if total_entries else 0
    podium_rate = len(top4) / total_entries * 100 if total_entries else 0

    # Seasons
    seasons = defaultdict(list)
    for r in results_sorted:
        seasons[get_season(r['dates'].split('/')[0])].append(r)
    season_keys = sorted(seasons.keys())

    # Seeding
    seeded = [r for r in results if r['seed'] and r['seed'] not in ['', 'WC']]
    seeded_losses = [r for r in seeded if r['seed'].isdigit() and int(r['rank_lo']) > int(r['seed'])]
    seeded_top = [r for r in seeded if r['seed'].isdigit() and int(r['seed']) <= 2]

    # Trend: compare recent vs earlier
    recent_season = season_keys[-1] if season_keys else None
    recent_results = seasons.get(recent_season, [])
    recent_wins = [r for r in recent_results if int(r['rank_lo']) == 1]
    earlier_seasons_results = [r for s in season_keys[:-1] for r in seasons[s]] if len(season_keys) >= 2 else []
    earlier_wins = [r for r in earlier_seasons_results if int(r['rank_lo']) == 1]

    # Specific tournament callouts
    jn_results = tier_results.get('JN', [])
    jn_wins = tier_wins.get('JN', [])
    sel_results = tier_results.get('SEL', [])
    orc_results = tier_results.get('ORC', [])
    orc_wins = tier_wins.get('ORC', [])
    olc_results = tier_results.get('OLC', [])
    olc_wins = tier_wins.get('OLC', [])
    crc_results = tier_results.get('CRC', [])
    crc_wins = tier_wins.get('CRC', [])

    # Regional travel
    regions = set()
    for t in all_tournaments:
        for region in ['NW', 'NE', 'SoCal', 'NorCal', 'South', 'Midwest']:
            if region in t: regions.add(region); break

    paras = []

    # Helper fragments
    state_from = f"from {home_state_name}" if home_state_name else "from parts unknown"
    ag_note = f" at the {current_ag} level" if current_ag else ""

    # Extra stats for narrative
    jn_champ_events = list(set(r['event'] for r in jn_wins)) if jn_wins else []
    sel_best = min((int(r['rank_lo']) for r in sel_results), default=999)
    jn_best = min((int(r['rank_lo']) for r in jn_results), default=999)

    # Per-tournament stats for specific callouts
    tourn_entries = defaultdict(list)
    for r in results_sorted:
        tourn_entries[r['tournament']].append(r)
    tourn_wins_ct = {t: sum(1 for r in rs if int(r['rank_lo'])==1) for t, rs in tourn_entries.items()}
    tourn_finals_ct = {t: sum(1 for r in rs if int(r['rank_lo'])==2) for t, rs in tourn_entries.items()}
    # Worst tournament by average rank
    tourn_avg = {t: sum(int(r['rank_lo']) for r in rs)/len(rs) for t, rs in tourn_entries.items() if len(rs) >= 2}
    worst_tourn = max(tourn_avg, key=tourn_avg.get) if tourn_avg else None
    # Best tournament where they had multi-win (for contrast)
    best_tourn = max(tourn_wins_ct, key=tourn_wins_ct.get) if tourn_wins_ct else None

    # First tournament & first win for origin story
    first_tourn = results_sorted[0]['tournament']
    first_win_r = next((r for r in results_sorted if int(r['rank_lo'])==1), None)

    # Multi-finals-loss tournaments
    multi_final_tourns = {t: ct for t, ct in tourn_finals_ct.items() if ct >= 2}

    # Doubles lowlight
    worst_doubles = sorted([r for r in d_results + x_results if int(r['rank_lo']) >= 17],
                           key=lambda r: -int(r['rank_lo']))

    # ═══════════════════════════════════════════════════════════════════════
    # PARAGRAPH 1: THE GRAND OPENING
    # Set the stage like a comedian walking out. Who is this person,
    # what's the headline stat, and why should the audience buckle in.
    # ═══════════════════════════════════════════════════════════════════════

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

    # ═══════════════════════════════════════════════════════════════════════
    # PARAGRAPH 2: THE ORIGIN STORY & CAREER ARC
    # Tell the story chronologically — the first tournament, the first
    # win (or lack thereof), the peak, and the fall from grace.
    # ═══════════════════════════════════════════════════════════════════════

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
                f"has not started yet — {len(seasons)} seasons later.")

    # Peak vs current
    if len(season_keys) >= 2:
        season_win_rates = {}
        for s in season_keys:
            sr = seasons[s]
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

    # ═══════════════════════════════════════════════════════════════════════
    # PARAGRAPH 3: THE FINALS PROBLEM
    # This is the emotional centerpiece — specific tournaments, specific
    # heartbreaks, the building pattern of almost-but-not-quite.
    # ═══════════════════════════════════════════════════════════════════════

    if len(finals) >= 3 or (len(finals) >= 2 and not wins):
        p3 = (f"But nothing — absolutely nothing — defines the {first} experience quite like the finals record. "
              f"Let us walk you through this, because the numbers alone do not do it justice. ")

        if len(finals) >= 3:
            p3 += (f"{first} has reached {len(finals)} championship matches across this career. "
                   f"That is {len(finals)} times standing one single match away from a title — the bracket won, "
                   f"the semifinal opponent dispatched, the crowd watching, the trophy right there — and "
                   f"{len(finals)} times walking away empty-handed. ")

            # Specific tournament callouts
            if multi_final_tourns:
                worst_t = max(multi_final_tourns, key=multi_final_tourns.get)
                worst_ct = multi_final_tourns[worst_t]
                worst_t_entries = tourn_entries[worst_t]
                worst_t_events = [r['event'] for r in worst_t_entries if int(r['rank_lo'])==2]
                p3 += (f"Take {worst_t}, where {first} entered {len(worst_t_entries)} events and came away with "
                       f"{worst_ct} runner-up finishes ({', '.join(worst_t_events)}). {worst_ct} chances at "
                       f"gold, {worst_ct} silver medals. That is not bad luck — that is an IDENTITY. ")

            # Singles vs doubles finals
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

    # ═══════════════════════════════════════════════════════════════════════
    # PARAGRAPH 4: DISCIPLINE & DOUBLES DEEP-DIVE
    # Singles identity vs doubles dependency. Partner drama as narrative.
    # ═══════════════════════════════════════════════════════════════════════

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
                   f"theory — nobody wants to be the partner who has to explain the loss over dinner.")
        elif not s_wins and not d_wins and not x_wins:
            p4 += (f"Three disciplines, {total_entries} entries, zero titles in any format. That is not "
                   f"versatility — that is just expanding the portfolio of failure across multiple asset classes. "
                   f"Diversification does not help when every investment returns zero.")
        else:
            p4 += (f"The breakdown: {len(s_wins)} singles, {len(d_wins)} doubles, {len(x_wins)} mixed "
                   f"title{'s' if len(x_wins)!=1 else ''}. A jack of all trades and a master of — well, let "
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

    # Partner narrative
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
                              f"carrying this doubles career on their back. Someone send {tp_name} a thank-you "
                              f"card, a gift basket, and maybe a chiropractor referral for all that heavy lifting.")
            elif tp_info['count'] >= 3:
                partner_p += (f"The most frequent partner is {tp_name} ({tp_info['count']} events, "
                              f"{tp_info['wins']} win{'s' if tp_info['wins']!=1 else ''}), which "
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

    # ═══════════════════════════════════════════════════════════════════════
    # PARAGRAPH 5: THE BIG STAGE & SEEDING
    # Tournament tiers, the gap between local and national, and the
    # comedy of being seeded and still losing.
    # ═══════════════════════════════════════════════════════════════════════

    p5_parts = []

    # Tier reality
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

    # Selection / JN specific
    if sel_results and not tier_wins.get('SEL') and len(sel_results) >= 2:
        sel_worst = max(int(r['rank_lo']) for r in sel_results)
        sel_entries = len(sel_results)
        p5_parts.append(
            f"At the Selection Event — where the stakes are as high as they get in American junior badminton — "
            f"{first} entered {sel_entries} events with results ranging from top-{sel_best} to a humbling "
            f"round-of-{sel_worst}. The Selection committee looked at {first}'s record and saw enough talent "
            f"to deserve an invitation. The bracket looked at {first} and said 'nah.'")

    if jn_results and not jn_wins:
        jn_entries = len(jn_results)
        jn_finals_ct = sum(1 for r in jn_results if int(r['rank_lo'])==2)
        if jn_finals_ct >= 2:
            p5_parts.append(
                f"Junior Nationals has been particularly cruel: {jn_entries} entries, {jn_finals_ct} finals "
                f"appearances, and zero titles. {first} has stood on the biggest stage in American junior "
                f"badminton, one match from the most important title in the sport, and come up short "
                f"{jn_finals_ct} times. That is the kind of heartbreak that builds character — or "
                f"destroys it. Time will tell.")
        elif jn_finals_ct == 1:
            p5_parts.append(
                f"At Junior Nationals — the Super Bowl of this sport — {first} has competed {jn_entries} "
                f"time{'s' if jn_entries!=1 else ''}, reaching the final once and coming away without the title. "
                f"So close to being a national champion, and yet so definitively not one.")
        elif jn_best <= 4:
            p5_parts.append(
                f"Junior Nationals has seen {first} {jn_entries} time{'s' if jn_entries!=1 else ''}, with a "
                f"best of top-{jn_best}. Close enough to the podium to feel the confetti, not close enough "
                f"to actually catch any.")
        else:
            p5_parts.append(
                f"At Junior Nationals, {first} has shown up {jn_entries} time{'s' if jn_entries!=1 else ''} "
                f"with a best of top-{jn_best}. "
                f"{'Respectable, but nobody writes home about a top-' + str(jn_best) + ' finish.' if jn_best <= 12 else 'Nobody is making a documentary about this.'}")

    # Seeding comedy
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

    # ═══════════════════════════════════════════════════════════════════════
    # PARAGRAPH 6: THE ROAD WARRIOR & PLAYING UP
    # Travel, ambition, age groups — the grand adventure of going
    # everywhere and achieving a 13% win rate.
    # ═══════════════════════════════════════════════════════════════════════

    p6_parts = []

    if playing_up_count >= 3 and len(ag_sorted) >= 3:
        up_results = [r for r in results if get_age_group(r['event']) and get_age_group(r['event']) != ag_sorted[0]]
        up_wins = [r for r in up_results if int(r['rank_lo']) == 1]
        up_best = min(int(r['rank_lo']) for r in up_results) if up_results else 999
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
        # Find a particularly bad far-away result
        far_bad = None
        if home_state_name:
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

    # ═══════════════════════════════════════════════════════════════════════
    # PARAGRAPH 7: THE LOWLIGHTS REEL & WORST MOMENTS
    # Specific disasters, early exits, the absolute rock bottom.
    # ═══════════════════════════════════════════════════════════════════════

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

    # ═══════════════════════════════════════════════════════════════════════
    # PARAGRAPH 8: THE CLOSING MONOLOGUE
    # The comedian gets sincere-ish, wraps the whole thing with a
    # callback and a backhanded toast.
    # ═══════════════════════════════════════════════════════════════════════

    if len(seasons) >= 4 and not wins:
        closer = (
            f"So here we are: {len(seasons)} seasons, {total_entries} entries, and not a single title to show "
            f"for any of it. Most people would have taken a long, hard look in the mirror by now. Most people "
            f"would have considered tennis, or chess, or literally any hobby with a higher return on investment "
            f"than junior badminton. But not {first}. {first} just fills out another entry form, packs the "
            f"racket bag, and drives to the next tournament with the unshakable optimism of someone who has "
            f"never read their own statistics. The definition of insanity is doing the same thing over and over "
            f"and expecting different results — and {first} has turned that into a multi-year lifestyle. "
            f"But you know what? The sport needs people like {first}. Every bracket needs a first-round opponent. "
            f"Every tournament needs entry fees. And every champion needs someone to beat on the way to the title. "
            f"So from the bottom of our hearts, {first}: thank you for your service. We mean that. Mostly.")
    elif len(seasons) >= 2 and wins:
        closer = (
            f"So where does this leave us? {len(seasons)} seasons deep, {len(wins)} "
            f"title{'s' if len(wins)!=1 else ''} to the name, {total_entries} entries, "
            f"and {total_entries - len(wins)} losses. If you squint at the highlights — the "
            f"{'national title' if jn_wins else 'Selection Event appearance' if sel_results else 'ORC victories' if orc_wins else 'local titles'}"
            f", the big wins, the moments of genuine brilliance — {first} looks like a player on the rise. "
            f"But we did not squint. We pulled up every single entry, every draw, every result, and what we "
            f"found is a player who {'chokes in finals like it is a hobby' if len(finals) >= 3 else 'has a complicated relationship with winning'}, "
            f"{'cannot win a singles match to save their life' if s_results and not s_wins else 'treats seeds like suggestions'  if len(seeded_losses) >= 3 else 'keeps searching for the right doubles partner like a bad dating app'  if num_partners >= 8 else 'is still figuring it out'}, "
            f"and travels the country paying entry fees with the enthusiasm of someone who truly believes the "
            f"next tournament will be different. And maybe it will be. But probably not. The data is not on "
            f"{first}'s side, but the human spirit is a powerful thing, and {first} has enough of it to "
            f"power a small city. So keep swinging, {first}. The shuttle tube industry thanks you. "
            f"The tournament organizers thank you. The opponents who padded their records against you "
            f"thank you most of all. We will be watching.")
    elif len(seasons) >= 2:
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


# ── Test on specific players ─────────────────────────────────────────────────
test_players = ['Jacob Ma', 'Grace Cheng']

print(f"\n{'='*80}")
print(f"ROAST SUMMARIES — TEST RUN")
print(f"{'='*80}")

for name in test_players:
    results = player_results.get(name, [])
    if not results:
        print(f"\n  Player '{name}' not found!")
        continue
    wins = sum(1 for r in results if int(r['rank_lo']) == 1)
    finals = sum(1 for r in results if int(r['rank_lo']) == 2)
    semis = sum(1 for r in results if int(r['rank_lo']) in [3,4])
    print(f"\n{'─'*80}")
    print(f"PLAYER: {name}")
    print(f"Stats: {len(results)} entries, {wins} wins, {finals} finals, {semis} semis")
    print(f"{'─'*80}")
    roast = generate_roast(name, results)
    # Strip HTML for terminal display
    clean = re.sub(r'<[^>]+>', '', roast).replace('</p>', '\n').replace('<p>', '')
    print(clean)
