#!/usr/bin/env python3
"""Generate a self-contained HTML rankings page from player_rankings.csv."""

import csv
import re
from collections import defaultdict
from html import escape

AGE_ORDER = ['U11', 'U13', 'U15', 'U17', 'U19']

# Load player slug mapping for links
player_slugs = {}
try:
    with open('data/player_slugs.csv', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            player_slugs[r['name']] = r['slug']
except FileNotFoundError:
    pass
DISC_ORDER = ['BS', 'GS', 'BD', 'GD', 'XD']
DISC_NAMES = {
    'BS': "Boys' Singles", 'GS': "Girls' Singles",
    'BD': "Boys' Doubles", 'GD': "Girls' Doubles",
    'XD': 'Mixed Doubles',
}

def shorten_detail(top4_detail):
    """Shorten tournament keys in detail string."""
    parts = top4_detail.split(' | ')
    short = []
    for d in parts:
        m = re.match(r'(\d{4}_\S+)\(rank (\S+) = (\d+) pts\)', d)
        if m:
            t = m.group(1).replace('2025_', '').replace('2026_', '')
            t = t.replace('_', ' ')
            short.append(f'{t} #{m.group(2)} ({m.group(3)})')
    return ' | '.join(short)

# Load data
rows = []
with open('data/player_rankings.csv', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        rows.append(r)

# Group
groups = defaultdict(list)
for r in rows:
    groups[(r['age_group'], r['discipline'])].append(r)
for k in groups:
    groups[k].sort(key=lambda x: -int(x['total_pts']))

# Build HTML
html_parts = []
html_parts.append('''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>USA Badminton Junior Rankings 2025-2026</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f7fa; color: #333; }
.header { background: linear-gradient(135deg, #1a3a5c, #2d6aa0); color: white; padding: 24px 20px 16px; text-align: center; }
.header h1 { font-size: 24px; margin-bottom: 4px; }
.header p { opacity: 0.8; font-size: 14px; }
.stats-link { display: inline-block; margin-top: 10px; padding: 8px 20px; background: rgba(255,255,255,0.15); color: white; text-decoration: none; border: 1px solid rgba(255,255,255,0.4); border-radius: 6px; font-size: 14px; font-weight: 500; transition: background 0.15s; }
.stats-link:hover { background: rgba(255,255,255,0.25); }
.controls { background: white; border-bottom: 1px solid #ddd; padding: 12px 20px; position: sticky; top: 0; z-index: 10; }
.age-tabs { display: flex; gap: 4px; justify-content: center; margin-bottom: 8px; }
.age-tabs button { padding: 8px 20px; border: 2px solid #2d6aa0; background: white; color: #2d6aa0; border-radius: 6px; cursor: pointer; font-weight: 600; font-size: 14px; transition: all 0.15s; }
.age-tabs button.active { background: #2d6aa0; color: white; }
.age-tabs button:hover:not(.active) { background: #e8f0f8; }
.disc-tabs { display: flex; gap: 4px; justify-content: center; margin-bottom: 8px; }
.disc-tabs button { padding: 6px 14px; border: 1px solid #ccc; background: white; color: #555; border-radius: 4px; cursor: pointer; font-size: 13px; transition: all 0.15s; }
.disc-tabs button.active { background: #555; color: white; border-color: #555; }
.disc-tabs button:hover:not(.active) { background: #f0f0f0; }
.search-box { display: flex; justify-content: center; }
.search-box input { padding: 8px 14px; border: 1px solid #ccc; border-radius: 6px; width: 300px; font-size: 14px; }
.search-box input:focus { outline: none; border-color: #2d6aa0; box-shadow: 0 0 0 2px rgba(45,106,160,0.2); }
.container { max-width: 1100px; margin: 0 auto; padding: 16px; }
.tab-content { display: none; }
.tab-content.active { display: block; }
table { width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
th { background: #f8f9fa; padding: 10px 12px; text-align: left; font-size: 13px; color: #666; border-bottom: 2px solid #e0e0e0; cursor: pointer; user-select: none; white-space: nowrap; }
th:hover { background: #eef1f5; }
th .sort-arrow { font-size: 10px; margin-left: 4px; opacity: 0.4; }
th.sorted-asc .sort-arrow::after { content: '▲'; opacity: 1; }
th.sorted-desc .sort-arrow::after { content: '▼'; opacity: 1; }
td { padding: 8px 12px; border-bottom: 1px solid #f0f0f0; font-size: 14px; }
tr:hover { background: #f8fbff; }
tr.hidden { display: none; }
.rank-col { width: 50px; text-align: center; font-weight: 600; color: #888; }
.pts-col { font-weight: 600; color: #2d6aa0; }
.count-col { text-align: center; color: #888; font-size: 13px; }
.detail-col { font-size: 12px; color: #777; }
.player-col { font-weight: 500; }
.rank-1 .rank-col { color: #d4a017; }
.rank-2 .rank-col { color: #8a8a8a; }
.rank-3 .rank-col { color: #b87333; }
.tab-info { text-align: center; color: #999; font-size: 13px; margin-top: 12px; }
@media (max-width: 768px) {
  .detail-col { display: none; }
  .age-tabs button { padding: 6px 12px; font-size: 13px; }
  .search-box input { width: 100%; }
}
</style>
</head>
<body>
<div class="header">
  <h1>USA Badminton Junior Rankings</h1>
  <p>2025-2026 Season &middot; Top 4 tournament scores &middot; Updated March 1, 2026</p>
  <a href="https://usjuniorbadmintonranking.com/stats" class="stats-link">Player Stats &rarr;</a>
</div>
<div class="controls">
  <div class="age-tabs" id="ageTabs">
''')

for age in AGE_ORDER:
    cls = ' class="active"' if age == 'U13' else ''
    html_parts.append(f'    <button{cls} data-age="{age}">{age}</button>\n')

html_parts.append('  </div>\n  <div class="disc-tabs" id="discTabs">\n')
for disc in DISC_ORDER:
    cls = ' class="active"' if disc == 'GS' else ''
    html_parts.append(f'    <button{cls} data-disc="{disc}">{DISC_NAMES[disc]}</button>\n')

html_parts.append('''  </div>
  <div class="search-box">
    <input type="text" id="searchInput" placeholder="Search player name...">
  </div>
</div>
<div class="container">
''')

# Generate tables
for age in AGE_ORDER:
    for disc in DISC_ORDER:
        key = (age, disc)
        data = groups.get(key, [])
        active = ' active' if age == 'U13' and disc == 'GS' else ''
        html_parts.append(f'<div class="tab-content{active}" data-age="{age}" data-disc="{disc}">\n')
        html_parts.append('<table>\n<thead><tr>')
        html_parts.append('<th class="rank-col" data-sort="num">Rank<span class="sort-arrow"></span></th>')
        html_parts.append('<th class="player-col" data-sort="str">Player<span class="sort-arrow"></span></th>')
        html_parts.append('<th class="pts-col" data-sort="num">Points<span class="sort-arrow"></span></th>')
        html_parts.append('<th class="count-col" data-sort="num">Played<span class="sort-arrow"></span></th>')
        html_parts.append('<th class="detail-col">Top 4 Results</th>')
        html_parts.append('</tr></thead>\n<tbody>\n')
        for i, r in enumerate(data, 1):
            rank_cls = f' rank-{i}' if i <= 3 else ''
            detail = escape(shorten_detail(r['top4_detail']))
            counted = r['tournaments_counted']
            total = r['tournaments_total']
            # Link player name to individual page
            player_name = r["player"]
            slug = player_slugs.get(player_name)
            if slug:
                player_html = f'<a href="players/{slug}.html" style="color:inherit;text-decoration:none;border-bottom:1px dashed #ccc">{escape(player_name)}</a>'
            else:
                player_html = escape(player_name)
            html_parts.append(
                f'<tr class="{rank_cls.strip()}">'
                f'<td class="rank-col">{i}</td>'
                f'<td class="player-col">{player_html}</td>'
                f'<td class="pts-col">{int(r["total_pts"]):,}</td>'
                f'<td class="count-col">{counted}/{total}</td>'
                f'<td class="detail-col">{detail}</td>'
                f'</tr>\n'
            )
        html_parts.append('</tbody>\n</table>\n')
        html_parts.append(f'<div class="tab-info">{len(data)} players</div>\n')
        html_parts.append('</div>\n')

html_parts.append('''</div>
<script>
const ageTabs = document.querySelectorAll('#ageTabs button');
const discTabs = document.querySelectorAll('#discTabs button');
const searchInput = document.getElementById('searchInput');
let currentAge = 'U13', currentDisc = 'GS';

function showTab() {
  document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
  const tab = document.querySelector(`.tab-content[data-age="${currentAge}"][data-disc="${currentDisc}"]`);
  if (tab) tab.classList.add('active');
  filterSearch();
}

ageTabs.forEach(btn => btn.addEventListener('click', () => {
  ageTabs.forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  currentAge = btn.dataset.age;
  showTab();
}));

discTabs.forEach(btn => btn.addEventListener('click', () => {
  discTabs.forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  currentDisc = btn.dataset.disc;
  showTab();
}));

function filterSearch() {
  const q = searchInput.value.toLowerCase().trim();
  const tab = document.querySelector('.tab-content.active');
  if (!tab) return;
  tab.querySelectorAll('tbody tr').forEach(row => {
    const name = row.querySelector('.player-col').textContent.toLowerCase();
    row.classList.toggle('hidden', q && !name.includes(q));
  });
}
searchInput.addEventListener('input', filterSearch);

// Column sorting
document.querySelectorAll('th[data-sort]').forEach(th => {
  th.addEventListener('click', () => {
    const table = th.closest('table');
    const tbody = table.querySelector('tbody');
    const idx = Array.from(th.parentNode.children).indexOf(th);
    const type = th.dataset.sort;
    const rows = Array.from(tbody.querySelectorAll('tr'));
    const isAsc = th.classList.contains('sorted-asc');
    table.querySelectorAll('th').forEach(h => h.classList.remove('sorted-asc', 'sorted-desc'));
    th.classList.add(isAsc ? 'sorted-desc' : 'sorted-asc');
    rows.sort((a, b) => {
      let va = a.children[idx].textContent.trim();
      let vb = b.children[idx].textContent.trim();
      if (type === 'num') {
        va = parseFloat(va.replace(/,/g, '')) || 0;
        vb = parseFloat(vb.replace(/,/g, '')) || 0;
        return isAsc ? vb - va : va - vb;
      }
      return isAsc ? vb.localeCompare(va) : va.localeCompare(vb);
    });
    rows.forEach(r => tbody.appendChild(r));
  });
});
</script>
</body>
</html>
''')

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(''.join(html_parts))

print(f'Generated index.html ({len(groups)} tabs, {len(rows)} total entries)')
