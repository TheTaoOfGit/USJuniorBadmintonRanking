#!/usr/bin/env python3
"""Compare our rankings with official usabjrrankings.org data."""

import csv
import json
import sys

# Load our rankings
ours = {}
with open('data/player_rankings.csv', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        key = (r['discipline'], r['age_group'], r['player'])
        ours[key] = int(r['total_pts'])

# Load official rankings from JSON (scraped separately)
with open('data/official_rankings.json', encoding='utf-8') as f:
    official = json.load(f)

age_order = ['U11', 'U13', 'U15', 'U17', 'U19']
disc_order = ['BS', 'GS', 'BD', 'GD', 'XD']

def name_key(n):
    t = n.strip().split()
    return (t[0].lower(), t[-1].lower()) if len(t) >= 2 else None

total_diffs = 0
for age in age_order:
    for disc in disc_order:
        cat_key = f'{disc}_{age}'
        if cat_key not in official:
            continue

        # Build lookup from our data for this category
        our_cat = {}
        for (d, a, name), pts in ours.items():
            if d == disc and a == age:
                nk = name_key(name)
                our_cat[nk] = (name, pts)

        # Compare
        diffs = []
        for orow in official[cat_key]:
            oname = orow['name']
            opts = orow['points']
            onk = name_key(oname)

            if onk in our_cat:
                our_name, our_pts = our_cat[onk]
                if our_pts != opts:
                    diffs.append(f"  {oname}: official={opts}, ours={our_pts} (diff={our_pts-opts:+d})")
                del our_cat[onk]
            else:
                diffs.append(f"  {oname}: official={opts}, NOT IN OURS")

        # Players in ours but not official
        for nk, (name, pts) in our_cat.items():
            diffs.append(f"  {name}: ours={pts}, NOT IN OFFICIAL")

        if diffs:
            print(f"\n{'='*60}")
            print(f"  {disc} {age} — {len(diffs)} differences")
            print(f"{'='*60}")
            for d in diffs:
                print(d)
            total_diffs += len(diffs)

print(f"\n\nTotal differences: {total_diffs}")
