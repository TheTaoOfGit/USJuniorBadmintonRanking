"""
Generate stats.html with sortable tables for overall + per-discipline stats.
Top 200 players by total points scored in each category.
"""
import csv, re, json
from collections import defaultdict

def normalize(name):
    s = re.sub(r'^\[.*?\]\s*', '', name.strip())
    s = re.sub(r'\s*\[\s*\]\s*$', '', s).strip()
    return s.title() if s else ''

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
        'pts_scored': 0, 'pts_against': 0, 'mw': 0, 'ml': 0,
        'games_played': 0, 'games_won': 0, 'games_lost': 0,
        'three_game_matches': 0, 'three_game_wins': 0, 'three_game_losses': 0,
        'straight_wins': 0, 'straight_losses': 0,
        'biggest_win_margin': 0, 'biggest_loss_margin': 0,
        'shutout_games_won': 0, 'shutout_games_lost': 0,
        'tournaments': set(),
    }

def process_match(stats_dict, row, disc_filter=None):
    event = row['event']
    disc = event.split()[0] if event else ''
    if disc_filter and disc != disc_filter:
        return
    games = parse_games(row['score'])
    if not games:
        return
    n = len(games)
    is3 = n == 3
    wgw = sum(1 for a, b in games if a > b)
    wgl = sum(1 for a, b in games if b > a)
    wp = sum(a for a, b in games)
    lp = sum(b for a, b in games)
    margin = wp - lp
    straight = wgw == 2 and wgl == 0
    shutouts = sum(1 for a, b in games if a > b and b == 0)

    is_doubles = disc in ('BD', 'GD', 'XD')
    for side, name_raw in [('w', row['winner']), ('l', row['loser'])]:
        if is_doubles:
            players = split_doubles(name_raw, event)
        else:
            players = [name_raw]
        for p in players:
            name = normalize(p)
            if name in JUNK:
                continue
            s = stats_dict[name]
            s['tournaments'].add(row['tournament'])
            s['games_played'] += n
            if side == 'w':
                s['pts_scored'] += wp
                s['pts_against'] += lp
                s['mw'] += 1
                s['games_won'] += wgw
                s['games_lost'] += wgl
                if is3:
                    s['three_game_matches'] += 1
                    s['three_game_wins'] += 1
                if straight:
                    s['straight_wins'] += 1
                if margin > s['biggest_win_margin']:
                    s['biggest_win_margin'] = margin
                s['shutout_games_won'] += shutouts
            else:
                s['pts_scored'] += lp
                s['pts_against'] += wp
                s['ml'] += 1
                s['games_won'] += wgl
                s['games_lost'] += wgw
                if is3:
                    s['three_game_matches'] += 1
                    s['three_game_losses'] += 1
                if straight:
                    s['straight_losses'] += 1
                if margin > s['biggest_loss_margin']:
                    s['biggest_loss_margin'] = margin
                s['shutout_games_lost'] += shutouts

# Read all matches once
all_rows = []
with open('data/match_details.csv', encoding='utf-8') as f:
    all_rows = list(csv.DictReader(f))

DISCIPLINES = {
    'all': 'Overall',
    'BS': 'Boys Singles',
    'GS': 'Girls Singles',
    'BD': 'Boys Doubles',
    'GD': 'Girls Doubles',
    'XD': 'Mixed Doubles',
}

TOP_N = 300

tabs_data = {}  # tab_key -> list of row dicts

for disc_key, disc_label in DISCIPLINES.items():
    stats = defaultdict(new_stats)
    filt = None if disc_key == 'all' else disc_key
    for row in all_rows:
        process_match(stats, row, disc_filter=filt)

    ranked = sorted(stats.items(), key=lambda x: -x[1]['pts_scored'])[:TOP_N]
    rows_out = []
    for i, (name, s) in enumerate(ranked, 1):
        tm = s['mw'] + s['ml']
        gp = s['games_played']
        if tm == 0:
            continue
        rows_out.append({
            'rank': i,
            'player': name,
            'tournaments_played': len(s['tournaments']),
            'matches': tm,
            'wins': s['mw'],
            'losses': s['ml'],
            'win_pct': round(100 * s['mw'] / tm, 1),
            'games_played': gp,
            'games_won': s['games_won'],
            'games_lost': s['games_lost'],
            'game_win_pct': round(100 * s['games_won'] / gp, 1) if gp else 0,
            'pts_scored': s['pts_scored'],
            'pts_against': s['pts_against'],
            'pt_diff': s['pts_scored'] - s['pts_against'],
            'avg_pts_per_match': round(s['pts_scored'] / tm, 1),
            'avg_pts_per_game': round(s['pts_scored'] / gp, 1) if gp else 0,
            'three_game_matches': s['three_game_matches'],
            'three_game_wins': s['three_game_wins'],
            'three_game_losses': s['three_game_losses'],
            'three_game_pct': round(100 * s['three_game_matches'] / tm, 1),
            'straight_set_wins': s['straight_wins'],
            'straight_set_losses': s['straight_losses'],
            'biggest_win_margin': s['biggest_win_margin'],
            'biggest_loss_margin': s['biggest_loss_margin'],
            'shutout_games_won': s['shutout_games_won'],
            'shutout_games_lost': s['shutout_games_lost'],
        })
    tabs_data[disc_key] = rows_out
    print(f"  {disc_label}: {len(rows_out)} players")

# Generate HTML
html = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>USA Badminton Junior Player Stats (2025-2026)</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f7fa; color: #1a1a2e; padding: 20px; }
  h1 { text-align: center; margin-bottom: 4px; font-size: 1.5rem; }
  .subtitle { text-align: center; color: #666; margin-bottom: 16px; font-size: 0.9rem; }

  /* Tabs */
  .tabs { display: flex; gap: 4px; margin-bottom: 0; justify-content: center; flex-wrap: wrap; }
  .tab {
    padding: 8px 18px; cursor: pointer; border: none; background: #dde;
    border-radius: 8px 8px 0 0; font-size: 14px; font-weight: 600; color: #555;
    transition: background 0.15s, color 0.15s;
  }
  .tab:hover { background: #ccd; }
  .tab.active { background: #1a1a2e; color: #fff; }

  .table-wrap { overflow-x: auto; background: #fff; border-radius: 0 8px 8px 8px; box-shadow: 0 1px 4px rgba(0,0,0,0.1); }
  table { border-collapse: collapse; width: 100%; min-width: 1400px; font-size: 13px; }
  thead { position: sticky; top: 0; z-index: 2; }
  th {
    background: #1a1a2e; color: #fff; padding: 8px 10px; text-align: right;
    cursor: pointer; user-select: none; white-space: nowrap; position: relative;
  }
  th:nth-child(2) { text-align: left; }
  th:hover { background: #2d2d5e; }
  th .arrow { font-size: 10px; margin-left: 3px; opacity: 0.4; }
  th.sort-asc .arrow::after { content: '\25B2'; }
  th.sort-desc .arrow::after { content: '\25BC'; }
  th.sort-asc .arrow, th.sort-desc .arrow { opacity: 1; }
  td { padding: 6px 10px; border-bottom: 1px solid #eee; text-align: right; white-space: nowrap; }
  td:nth-child(2) { text-align: left; font-weight: 600; }
  tr:hover td { background: #f0f4ff; }
  tr:nth-child(even) td { background: #fafbfc; }
  tr:nth-child(even):hover td { background: #f0f4ff; }
  .pos { color: #999; font-weight: normal; }
  .good { color: #16a34a; }
  .bad { color: #dc2626; }

  /* Tooltips */
  .tip { position: relative; }
  .tip::after {
    content: attr(data-tip); position: absolute; top: 100%; left: 50%; transform: translateX(-50%);
    background: #444; color: #fff; padding: 6px 12px; border-radius: 6px; font-size: 12px;
    font-weight: normal; letter-spacing: 0;
    white-space: nowrap; pointer-events: none; opacity: 0; transition: opacity 0.2s;
    z-index: 10; margin-top: 4px; box-shadow: 0 2px 8px rgba(0,0,0,0.3);
  }
  .tip::before {
    content: ''; position: absolute; top: 100%; left: 50%; transform: translateX(-50%);
    border: 5px solid transparent; border-bottom-color: #444;
    pointer-events: none; opacity: 0; transition: opacity 0.2s; z-index: 10;
  }
  .tip:hover::after, .tip:hover::before { opacity: 1; }
  th:first-child.tip::after { left: 0; transform: none; }
  th:last-child.tip::after, th:nth-last-child(2).tip::after { left: auto; right: 0; transform: none; }
  th:first-child.tip::before { left: 15px; transform: none; }
  th:last-child.tip::before, th:nth-last-child(2).tip::before { left: auto; right: 15px; transform: none; }

  .count { text-align: center; color: #888; font-size: 12px; margin-top: 8px; }

  .nav-link { color: #3b5998; text-decoration: none; font-weight: 600; }
  .nav-link:hover { text-decoration: underline; }

  /* Legend */
  .legend { max-width: 900px; margin: 32px auto 0; background: #fff; border-radius: 8px; box-shadow: 0 1px 4px rgba(0,0,0,0.1); padding: 24px 32px; }
  .legend h2 { font-size: 1.1rem; margin-bottom: 12px; color: #1a1a2e; }
  .legend table { min-width: 0; width: 100%; font-size: 13px; }
  .legend th { background: #eef; color: #1a1a2e; text-align: left; padding: 6px 10px; cursor: default; }
  .legend th:hover { background: #eef; }
  .legend td { text-align: left; padding: 6px 10px; font-weight: normal; }
  .legend td:first-child { font-weight: 700; white-space: nowrap; width: 60px; }
  .legend .section-label td { background: #f5f7fa; font-weight: 600; color: #555; padding-top: 10px; }
</style>
</head>
<body>

<h1>USA Badminton Junior Player Game Stats</h1>
<p class="subtitle">2025-2026 Season &mdash; Top 300 per discipline &mdash; Updated March 6, 2026</p>
<p class="subtitle"><a href="https://usjuniorbadmintonranking.com/" class="nav-link">Ranking</a> | <a href="#legend" class="nav-link">Column Legend</a></p>

<div class="tabs" id="tabs"></div>
<div class="table-wrap">
  <table id="stats">
    <thead id="thead"></thead>
    <tbody id="tbody"></tbody>
  </table>
</div>
<p class="count" id="count"></p>

<div class="legend" id="legend">
  <h2>Column Legend</h2>
  <table>
    <thead><tr><th>Column</th><th>Description</th></tr></thead>
    <tbody>
      <tr class="section-label"><td colspan="2">Basic Info</td></tr>
      <tr><td>#</td><td>Rank by total rally points scored across all games</td></tr>
      <tr><td>Player</td><td>Player name (stats combined across all age groups within the selected discipline)</td></tr>
      <tr><td>T</td><td>Tournaments played: number of distinct tournaments the player competed in</td></tr>
      <tr class="section-label"><td colspan="2">Match Record</td></tr>
      <tr><td>M</td><td>Matches: total matches played (wins + losses)</td></tr>
      <tr><td>W</td><td>Wins: total matches won</td></tr>
      <tr><td>L</td><td>Losses: total matches lost</td></tr>
      <tr><td>W%</td><td>Win percentage: match win rate (wins &divide; matches &times; 100)</td></tr>
      <tr class="section-label"><td colspan="2">Game Record</td></tr>
      <tr><td>GP</td><td>Games played: total individual games played. Each match is best-of-3 games (2 or 3 games per match)</td></tr>
      <tr><td>GW</td><td>Games won: individual games won (each game is played to 21 points)</td></tr>
      <tr><td>GL</td><td>Games lost: individual games lost</td></tr>
      <tr><td>G%</td><td>Game win percentage: game win rate (games won &divide; games played &times; 100)</td></tr>
      <tr class="section-label"><td colspan="2">Rally Points</td></tr>
      <tr><td>Pts</td><td>Points scored: total rally points scored across all games in the season</td></tr>
      <tr><td>Agst</td><td>Points against: total rally points conceded to opponents</td></tr>
      <tr><td>Diff</td><td>Point differential: points scored minus points conceded. Green = positive, red = negative</td></tr>
      <tr><td>P/M</td><td>Points per match: average rally points scored per match</td></tr>
      <tr><td>P/G</td><td>Points per game: average rally points scored per game (theoretical max around 21)</td></tr>
      <tr class="section-label"><td colspan="2">3-Game Matches (Deciding Game)</td></tr>
      <tr><td>3GM</td><td>3-game matches: number of matches that went to a deciding 3rd game</td></tr>
      <tr><td>3GW</td><td>3-game wins: matches won after going to a 3rd game (clutch wins)</td></tr>
      <tr><td>3GL</td><td>3-game losses: matches lost after going to a 3rd game</td></tr>
      <tr><td>3G%</td><td>3-game percentage: what % of all matches went to a deciding 3rd game</td></tr>
      <tr class="section-label"><td colspan="2">Dominance</td></tr>
      <tr><td>SSW</td><td>Straight-set wins: matches won 2-0 without dropping a game</td></tr>
      <tr><td>SSL</td><td>Straight-set losses: matches lost 0-2 without winning a game</td></tr>
      <tr><td>BWM</td><td>Biggest win margin: largest total rally point differential in a single match win</td></tr>
      <tr><td>BLM</td><td>Biggest loss margin: largest total rally point differential in a single match loss</td></tr>
    </tbody>
  </table>
</div>

<script>
const TABS = TABS_JSON;
const DATA = DATA_JSON;

const COLS = [
  {key:'rank',type:'num',label:'#',tip:'Rank by total rally points scored'},
  {key:'player',type:'str',label:'Player',tip:'Player name'},
  {key:'tournaments_played',type:'num',label:'T',tip:'Tournaments: number of distinct tournaments played'},
  {key:'matches',type:'num',label:'M',tip:'Matches: total matches played (wins + losses)'},
  {key:'wins',type:'num',label:'W',tip:'Wins: matches won'},
  {key:'losses',type:'num',label:'L',tip:'Losses: matches lost'},
  {key:'win_pct',type:'num',label:'W%',tip:'Win %: match win rate (wins / matches \u00d7 100)'},
  {key:'games_played',type:'num',label:'GP',tip:'Games Played: each match has 2-3 games (best of 3, each to 21)'},
  {key:'games_won',type:'num',label:'GW',tip:'Games Won: individual games won'},
  {key:'games_lost',type:'num',label:'GL',tip:'Games Lost: individual games lost'},
  {key:'game_win_pct',type:'num',label:'G%',tip:'Game Win %: game win rate (games won / played \u00d7 100)'},
  {key:'pts_scored',type:'num',label:'Pts',tip:'Points Scored: total rally points scored across all games'},
  {key:'pts_against',type:'num',label:'Agst',tip:'Points Against: total rally points conceded'},
  {key:'pt_diff',type:'num',label:'Diff',tip:'Point Diff: points scored minus points conceded'},
  {key:'avg_pts_per_match',type:'num',label:'P/M',tip:'Pts/Match: average rally points scored per match'},
  {key:'avg_pts_per_game',type:'num',label:'P/G',tip:'Pts/Game: average rally points scored per game (max ~21)'},
  {key:'three_game_matches',type:'num',label:'3GM',tip:'3-Game Matches: matches that went to a deciding 3rd game'},
  {key:'three_game_wins',type:'num',label:'3GW',tip:'3-Game Wins: matches won that went to 3 games (clutch wins)'},
  {key:'three_game_losses',type:'num',label:'3GL',tip:'3-Game Losses: matches lost that went to 3 games'},
  {key:'three_game_pct',type:'num',label:'3G%',tip:'3-Game %: percentage of all matches that went to 3 games'},
  {key:'straight_set_wins',type:'num',label:'SSW',tip:'Straight-Set Wins: matches won 2-0 without dropping a game'},
  {key:'straight_set_losses',type:'num',label:'SSL',tip:'Straight-Set Losses: matches lost 0-2 without winning a game'},
  {key:'biggest_win_margin',type:'num',label:'BWM',tip:'Biggest Win Margin: largest total point diff in a single match win'},
  {key:'biggest_loss_margin',type:'num',label:'BLM',tip:'Biggest Loss Margin: largest total point diff in a single match loss'},
];

const numCols = new Set(COLS.filter(c => c.type === 'num').map(c => c.key));

function fmt(val, col) {
  if (!numCols.has(col)) return val;
  const n = parseFloat(val);
  if (col === 'pt_diff') return (n >= 0 ? '+' : '') + n.toLocaleString();
  if (['pts_scored', 'pts_against'].includes(col)) return n.toLocaleString();
  if (['win_pct', 'game_win_pct', 'three_game_pct', 'avg_pts_per_match', 'avg_pts_per_game'].includes(col))
    return n.toFixed(1);
  return val;
}

function colorClass(col, val) {
  const n = parseFloat(val);
  if (col === 'pt_diff') return n > 0 ? 'good' : n < 0 ? 'bad' : '';
  if (col === 'win_pct' || col === 'game_win_pct') return n >= 75 ? 'good' : n < 55 ? 'bad' : '';
  return '';
}

// Build header once
const thead = document.getElementById('thead');
const tr = document.createElement('tr');
COLS.forEach(c => {
  const th = document.createElement('th');
  th.dataset.col = c.key;
  th.dataset.type = c.type;
  th.className = 'tip';
  th.dataset.tip = c.tip;
  th.innerHTML = c.label + '<span class="arrow"></span>';
  tr.appendChild(th);
});
thead.appendChild(tr);

const tbody = document.getElementById('tbody');
const countEl = document.getElementById('count');
let currentTab = 'all';
let currentData = [];
let sortCol = null, sortDir = 1;

function render() {
  tbody.innerHTML = currentData.map((r, i) => {
    return '<tr>' + COLS.map(c => {
      if (c.key === 'rank') return `<td class="pos">${i + 1}</td>`;
      const v = r[c.key];
      const cc = colorClass(c.key, v);
      return `<td${cc ? ` class="${cc}"` : ''}>${fmt(v, c.key)}</td>`;
    }).join('') + '</tr>';
  }).join('');
  countEl.textContent = `Showing ${currentData.length} players`;
}

function switchTab(key) {
  currentTab = key;
  currentData = DATA[key].slice();
  sortCol = null;
  sortDir = 1;
  document.querySelectorAll('.tab').forEach(t => t.classList.toggle('active', t.dataset.key === key));
  document.querySelectorAll('th').forEach(th => th.classList.remove('sort-asc', 'sort-desc'));
  render();
}

// Build tabs
const tabsEl = document.getElementById('tabs');
TABS.forEach(([key, label]) => {
  const btn = document.createElement('button');
  btn.className = 'tab';
  btn.dataset.key = key;
  btn.textContent = label;
  btn.addEventListener('click', () => switchTab(key));
  tabsEl.appendChild(btn);
});

// Sort on header click
document.querySelectorAll('th[data-col]').forEach(th => {
  th.addEventListener('click', () => {
    const col = th.dataset.col;
    const isNum = th.dataset.type === 'num';
    if (sortCol === col) { sortDir *= -1; }
    else { sortCol = col; sortDir = isNum ? -1 : 1; }
    document.querySelectorAll('th').forEach(t => t.classList.remove('sort-asc', 'sort-desc'));
    th.classList.add(sortDir === 1 ? 'sort-asc' : 'sort-desc');
    currentData.sort((a, b) => {
      let va = a[col], vb = b[col];
      if (isNum) { va = parseFloat(va) || 0; vb = parseFloat(vb) || 0; }
      else { va = (va||'').toLowerCase(); vb = (vb||'').toLowerCase(); }
      return va < vb ? -sortDir : va > vb ? sortDir : 0;
    });
    render();
  });
});

switchTab('all');
</script>
</body>
</html>
'''

tabs_list = [['all', 'Overall'], ['BS', 'Boys Singles'], ['GS', 'Girls Singles'],
             ['BD', 'Boys Doubles'], ['GD', 'Girls Doubles'], ['XD', 'Mixed Doubles']]

html = html.replace('TABS_JSON', json.dumps(tabs_list))
html = html.replace('DATA_JSON', json.dumps(tabs_data))

with open('stats.html', 'w', encoding='utf-8') as f:
    f.write(html)

print(f"Wrote stats.html")
