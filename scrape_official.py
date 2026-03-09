#!/usr/bin/env python3
"""Scrape official rankings from usabjrrankings.org for comparison."""
import json
import re
import urllib.request

AGE_ORDER = ['U11', 'U13', 'U15', 'U17', 'U19']
DISC_ORDER = ['BS', 'GS', 'BD', 'GD', 'XD']

results = {}

for age in AGE_ORDER:
    for disc in DISC_ORDER:
        url = f'https://usabjrrankings.org/?age_group={age}&category={disc}&date=2026-03-01'
        print(f'Fetching {disc} {age}...', end=' ', flush=True)
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=30) as resp:
            html = resp.read().decode('utf-8')

        players = []
        row_pat = re.compile(
            r'<tr>\s*<td>\s*(\d+)\s*</td>\s*<td>(\d+)</td>\s*'
            r'<td><a[^>]*>(.*?)</a></td>\s*<td>\s*([\d,]+)\s*</td>\s*</tr>',
            re.DOTALL
        )
        for m in row_pat.finditer(html):
            rank = int(m.group(1))
            usab_id = m.group(2)
            name = m.group(3).strip()
            points = int(m.group(4).replace(',', ''))
            players.append({'rank': rank, 'usab_id': usab_id, 'name': name, 'points': points})

        print(f'{len(players)} players')
        results[f'{disc}_{age}'] = players

with open('data/official_rankings.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

total = sum(len(v) for v in results.values())
print(f'\nSaved {total} entries across {len(results)} categories to data/official_rankings.json')
