"""Generate a PDF and long JPG report for a player's tournament results."""
import csv, os, sys, re
from collections import defaultdict
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from PIL import Image, ImageDraw, ImageFont

DRAWS_DIR = "data/draws"
PLAYER_NAME = "Mikael Chang"
OUT_PDF = "data/mikael_chang_results.pdf"
OUT_JPG = "data/mikael_chang_results.jpg"

# ── Collect results ──────────────────────────────────────────────────────────
def load_results(player_name):
    results = []
    for fn in sorted(os.listdir(DRAWS_DIR)):
        if not fn.endswith('.csv'):
            continue
        with open(os.path.join(DRAWS_DIR, fn), encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                p = row['player']
                # Check if player name appears (as singles or in doubles)
                if player_name in p:
                    results.append(row)
    # Sort by date
    results.sort(key=lambda r: r['dates'].split('/')[0])
    return results

def parse_partner(player_field, player_name):
    """Extract partner name from doubles player field."""
    # Remove seeds like [1], [3/4], [WC], etc.
    clean = re.sub(r'\s*\[[\w/]+\]', '', player_field).strip()
    if clean == player_name:
        return None
    # Try to split - player_name could be at start or end
    if clean.startswith(player_name):
        return clean[len(player_name):]
    if clean.endswith(player_name):
        return clean[:-len(player_name)]
    return clean.replace(player_name, '').strip()

def format_rank(rank_lo, rank_hi):
    lo, hi = int(rank_lo), int(rank_hi)
    if lo == hi:
        return str(lo)
    return f"{lo}-{hi}"

def get_season(date_str):
    """Determine season from start date."""
    year, month = int(date_str[:4]), int(date_str[5:7])
    if month >= 8:
        return f"{year}-{year+1}"
    else:
        return f"{year-1}-{year}"

results = load_results(PLAYER_NAME)
print(f"Found {len(results)} results for {PLAYER_NAME}")

# Group by season
seasons = defaultdict(list)
for r in results:
    start_date = r['dates'].split('/')[0]
    season = get_season(start_date)
    seasons[season].append(r)

# ── PDF Generation ───────────────────────────────────────────────────────────
def generate_pdf(results_by_season, player_name, out_path):
    doc = SimpleDocTemplate(out_path, pagesize=letter,
                           topMargin=0.5*inch, bottomMargin=0.5*inch,
                           leftMargin=0.5*inch, rightMargin=0.5*inch)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('Title2', parent=styles['Title'], fontSize=18, spaceAfter=6)
    subtitle_style = ParagraphStyle('Subtitle2', parent=styles['Heading2'], fontSize=13,
                                     textColor=colors.HexColor('#333333'), spaceAfter=4)
    season_style = ParagraphStyle('Season', parent=styles['Heading2'], fontSize=14,
                                   textColor=colors.HexColor('#1a5276'), spaceBefore=12, spaceAfter=6)
    note_style = ParagraphStyle('Note', parent=styles['Normal'], fontSize=8,
                                 textColor=colors.grey, spaceAfter=2)

    elements = []
    elements.append(Paragraph(f"{player_name} — Tournament Results", title_style))
    elements.append(Paragraph(f"{sum(len(v) for v in results_by_season.values())} results across "
                              f"{len(set(r['tournament'] for s in results_by_season.values() for r in s))} tournaments",
                              subtitle_style))
    elements.append(Spacer(1, 8))

    header = ['Tournament', 'Date', 'Event', 'Partner', 'Seed', 'Rank', 'Round']
    col_widths = [2.0*inch, 0.9*inch, 0.6*inch, 1.3*inch, 0.4*inch, 0.45*inch, 0.85*inch]

    for season in sorted(results_by_season.keys()):
        rows = results_by_season[season]
        elements.append(Paragraph(f"Season {season}", season_style))

        cell_style = ParagraphStyle('Cell', fontSize=7, leading=9)
        bold_style = ParagraphStyle('BoldCell', fontSize=7, leading=9, fontName='Helvetica-Bold')

        table_data = [[Paragraph(f"<b>{h}</b>", cell_style) for h in header]]
        for r in rows:
            start = r['dates'].split('/')[0]
            month_names = ['', 'Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
            y, m, d = start.split('-')
            date_str = f"{month_names[int(m)]} {y}"

            partner = parse_partner(r['player'], player_name)
            partner = partner or '—'
            rank_str = format_rank(r['rank_lo'], r['rank_hi'])
            seed = r['seed'] if r['seed'] else ''
            elim = r['elim_round']

            # Highlight top results
            rank_lo = int(r['rank_lo'])
            if rank_lo == 1:
                rs = Paragraph(f"<b><font color='#d4af37'>🏆 {rank_str}</font></b>", cell_style)
            elif rank_lo <= 3:
                rs = Paragraph(f"<b><font color='#1a5276'>{rank_str}</font></b>", cell_style)
            elif rank_lo <= 4:
                rs = Paragraph(f"<b>{rank_str}</b>", cell_style)
            else:
                rs = Paragraph(rank_str, cell_style)

            row_data = [
                Paragraph(r['tournament'], cell_style),
                Paragraph(date_str, cell_style),
                Paragraph(r['event'], cell_style),
                Paragraph(partner, cell_style),
                Paragraph(seed, cell_style),
                rs,
                Paragraph(elim, cell_style),
            ]
            table_data.append(row_data)

        t = Table(table_data, colWidths=col_widths, repeatRows=1)
        style_cmds = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a5276')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]
        # Alternate row colors
        for i in range(1, len(table_data)):
            if i % 2 == 0:
                style_cmds.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor('#f0f4f8')))
            # Highlight winner rows
            rank_lo = int(rows[i-1]['rank_lo'])
            if rank_lo == 1:
                style_cmds.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor('#fef9e7')))

        t.setStyle(TableStyle(style_cmds))
        elements.append(t)
        elements.append(Spacer(1, 4))

    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"Generated from USA Badminton tournament data — {len(results)} total entries",
                              note_style))

    doc.build(elements)
    print(f"PDF saved to {out_path}")

generate_pdf(seasons, PLAYER_NAME, OUT_PDF)

# ── JPG Generation ───────────────────────────────────────────────────────────
def generate_jpg(results_by_season, player_name, out_path):
    # Layout constants
    margin = 40
    col_widths = [280, 100, 80, 180, 60, 60, 120]
    row_height = 24
    header_height = 30
    season_header_height = 36
    total_width = sum(col_widths) + 2 * margin
    headers = ['Tournament', 'Date', 'Event', 'Partner', 'Seed', 'Rank', 'Round']

    # Calculate total height
    title_height = 80
    total_rows = sum(len(v) for v in results_by_season.values())
    num_seasons = len(results_by_season)
    total_height = (title_height + num_seasons * (season_header_height + header_height) +
                    total_rows * row_height + margin * 2 + 30)

    img = Image.new('RGB', (total_width, total_height), '#ffffff')
    draw = ImageDraw.Draw(img)

    # Try to load fonts
    try:
        font_title = ImageFont.truetype("arial.ttf", 24)
        font_subtitle = ImageFont.truetype("arial.ttf", 14)
        font_season = ImageFont.truetype("arialbd.ttf", 16)
        font_header = ImageFont.truetype("arialbd.ttf", 12)
        font_cell = ImageFont.truetype("arial.ttf", 11)
        font_bold = ImageFont.truetype("arialbd.ttf", 11)
        font_note = ImageFont.truetype("arial.ttf", 10)
    except:
        font_title = ImageFont.load_default()
        font_subtitle = font_title
        font_season = font_title
        font_header = font_title
        font_cell = font_title
        font_bold = font_title
        font_note = font_title

    y = margin
    # Title
    draw.text((margin, y), f"{player_name} — Tournament Results", fill='#1a5276', font=font_title)
    y += 36
    total_tournaments = len(set(r['tournament'] for s in results_by_season.values() for r in s))
    draw.text((margin, y), f"{total_rows} results across {total_tournaments} tournaments", fill='#555555', font=font_subtitle)
    y += 30

    month_names = ['', 'Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']

    for season in sorted(results_by_season.keys()):
        rows = results_by_season[season]
        # Season header
        y += 8
        draw.rectangle([(margin, y), (total_width - margin, y + season_header_height - 4)], fill='#eaf2f8')
        draw.text((margin + 8, y + 8), f"Season {season}", fill='#1a5276', font=font_season)
        y += season_header_height

        # Table header
        x = margin
        draw.rectangle([(margin, y), (total_width - margin, y + header_height)], fill='#1a5276')
        for i, h in enumerate(headers):
            draw.text((x + 4, y + 7), h, fill='white', font=font_header)
            x += col_widths[i]
        y += header_height

        # Data rows
        for idx, r in enumerate(rows):
            bg = '#fef9e7' if int(r['rank_lo']) == 1 else ('#f0f4f8' if idx % 2 == 0 else '#ffffff')
            draw.rectangle([(margin, y), (total_width - margin, y + row_height)], fill=bg)
            # Grid line
            draw.line([(margin, y + row_height), (total_width - margin, y + row_height)], fill='#cccccc')

            start = r['dates'].split('/')[0]
            yr, mo, dy = start.split('-')
            date_str = f"{month_names[int(mo)]} {yr}"
            partner = parse_partner(r['player'], player_name) or '—'
            rank_str = format_rank(r['rank_lo'], r['rank_hi'])
            seed = r['seed'] if r['seed'] else ''
            elim = r['elim_round']

            rank_lo = int(r['rank_lo'])
            if rank_lo == 1:
                rank_display = f"1 W"
                rank_color = '#b7950b'
                rank_font = font_bold
            elif rank_lo <= 4:
                rank_display = rank_str
                rank_color = '#1a5276'
                rank_font = font_bold
            else:
                rank_display = rank_str
                rank_color = '#333333'
                rank_font = font_cell

            values = [
                (r['tournament'], '#333333', font_cell),
                (date_str, '#333333', font_cell),
                (r['event'], '#333333', font_cell),
                (partner, '#333333', font_cell),
                (seed, '#333333', font_cell),
                (rank_display, rank_color, rank_font),
                (elim, '#555555', font_cell),
            ]

            x = margin
            for i, (val, color, fnt) in enumerate(values):
                # Truncate if too long
                max_chars = col_widths[i] // 7
                if len(val) > max_chars:
                    val = val[:max_chars-2] + '..'
                draw.text((x + 4, y + 5), val, fill=color, font=fnt)
                x += col_widths[i]

            y += row_height

    y += 16
    draw.text((margin, y), f"Generated from USA Badminton tournament data", fill='#999999', font=font_note)

    img.save(out_path, quality=95)
    print(f"JPG saved to {out_path} ({img.size[0]}x{img.size[1]})")

generate_jpg(seasons, PLAYER_NAME, OUT_JPG)
