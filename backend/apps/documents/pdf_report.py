"""
Génération du rapport mensuel PDF — Budget Master.
"""
import io
from decimal import Decimal
from django.db.models import Sum
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER


# ── Palette ──────────────────────────────────────────────────────────────────
C_BG      = colors.HexColor('#0B0F1A')
C_SURFACE = colors.HexColor('#111827')
C_ACCENT  = colors.HexColor('#00D4AA')
C_GREEN   = colors.HexColor('#34D399')
C_RED     = colors.HexColor('#F87171')
C_ORANGE  = colors.HexColor('#FBBF24')
C_BLUE    = colors.HexColor('#60A5FA')
C_PURPLE  = colors.HexColor('#A78BFA')
C_TEXT    = colors.HexColor('#F0F4F8')
C_MUTED   = colors.HexColor('#6B7280')
C_BORDER  = colors.HexColor('#1F2937')
W = A4[0]


def _styles():
    base = getSampleStyleSheet()
    return {
        'h1': ParagraphStyle('h1', fontSize=22, textColor=C_TEXT, fontName='Helvetica-Bold', spaceAfter=2),
        'h2': ParagraphStyle('h2', fontSize=11, textColor=C_ACCENT, fontName='Helvetica-Bold', spaceBefore=14, spaceAfter=6),
        'label': ParagraphStyle('label', fontSize=7.5, textColor=C_MUTED, fontName='Helvetica', spaceAfter=2, leading=10),
        'value': ParagraphStyle('value', fontSize=13, textColor=C_TEXT, fontName='Helvetica-Bold', leading=16),
        'small': ParagraphStyle('small', fontSize=8, textColor=C_MUTED, fontName='Helvetica', leading=11),
        'normal': ParagraphStyle('normal', fontSize=9, textColor=C_TEXT, fontName='Helvetica', leading=13),
        'sub': ParagraphStyle('sub', fontSize=8.5, textColor=colors.HexColor('#9CA3AF'), fontName='Helvetica'),
    }


def _fmt(amount, sign=False):
    v = float(amount)
    s = f"{abs(v):,.0f} €".replace(',', ' ')
    if sign:
        return f"+{s}" if v >= 0 else f"-{s}"
    return s


def generate_monthly_report(user, month: str) -> bytes:
    """
    Génère un rapport PDF mensuel et retourne les bytes du fichier.
    month: "YYYY-MM"
    """
    from apps.transactions.models import Transaction
    from apps.categories.models import Category, CategoryBudget
    from apps.savings.models import SavingsRule

    year, m = map(int, month.split('-'))
    buf = io.BytesIO()

    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=18*mm, rightMargin=18*mm,
        topMargin=16*mm, bottomMargin=16*mm,
    )

    S = _styles()
    story = []

    # ── Header ────────────────────────────────────────────────────────────────
    month_label = f"{['Janvier','Février','Mars','Avril','Mai','Juin','Juillet','Août','Septembre','Octobre','Novembre','Décembre'][m-1]} {year}"
    header_data = [[
        Paragraph(f"<b>Budget Master</b>", ParagraphStyle('brand', fontSize=14, textColor=C_ACCENT, fontName='Helvetica-Bold')),
        Paragraph(f"Rapport mensuel — {month_label}", ParagraphStyle('month', fontSize=10, textColor=C_MUTED, fontName='Helvetica', alignment=TA_RIGHT)),
    ]]
    header_table = Table(header_data, colWidths=[W*0.5 - 18*mm, W*0.5 - 18*mm])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(header_table)
    story.append(HRFlowable(width='100%', thickness=1, color=C_ACCENT, spaceAfter=12))

    # ── KPIs ─────────────────────────────────────────────────────────────────
    qs = Transaction.objects.filter(user=user, date__year=year, date__month=m)
    income   = float(qs.filter(type='income').aggregate(s=Sum('amount'))['s'] or 0)
    expenses = float(qs.filter(type='expense').aggregate(s=Sum('amount'))['s'] or 0)
    savings  = float(qs.filter(type='saving').aggregate(s=Sum('amount'))['s'] or 0)
    balance  = income - expenses - savings

    story.append(Paragraph("Vue d'ensemble", S['h2']))

    kpi_data = [[
        _kpi_cell("REVENUS", income, C_GREEN, S),
        _kpi_cell("DÉPENSES", expenses, C_RED, S),
        _kpi_cell("ÉPARGNE", savings, C_BLUE, S),
        _kpi_cell("SOLDE", balance, C_GREEN if balance >= 0 else C_RED, S),
    ]]
    kpi_table = Table(kpi_data, colWidths=[(W - 36*mm) / 4] * 4, hAlign='LEFT')
    kpi_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), C_SURFACE),
        ('BOX', (0,0), (0,0), 0.5, C_BORDER),
        ('BOX', (1,0), (1,0), 0.5, C_BORDER),
        ('BOX', (2,0), (2,0), 0.5, C_BORDER),
        ('BOX', (3,0), (3,0), 0.5, C_BORDER),
        ('ROUNDEDCORNERS', [4]),
        ('TOPPADDING', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 12))

    # ── Règle 50/30/20 ────────────────────────────────────────────────────────
    story.append(Paragraph("Règle 50 / 30 / 20", S['h2']))

    try:
        rule = SavingsRule.objects.get(user=user, active=True)
        targets = {'needs': float(rule.needs_target), 'wants': float(rule.wants_target), 'savings': float(rule.savings_target)}
    except SavingsRule.DoesNotExist:
        targets = {'needs': 50, 'wants': 30, 'savings': 20}

    by_bucket = {}
    for row in qs.filter(type='expense').values('category__rule_bucket').annotate(t=Sum('amount')):
        b = row['category__rule_bucket'] or 'wants'
        by_bucket[b] = float(row['t'] or 0)

    sav_rate = savings / income * 100 if income else 0
    rule_rows = [
        [Paragraph('<b>Bucket</b>', S['small']), Paragraph('<b>Cible</b>', S['small']),
         Paragraph('<b>Réel</b>', S['small']), Paragraph('<b>Écart</b>', S['small']),
         Paragraph('<b>Montant</b>', S['small'])],
    ]
    bucket_info = [
        ('Besoins',  'needs',   by_bucket.get('needs', 0),   C_BLUE),
        ('Envies',   'wants',   by_bucket.get('wants', 0),   C_PURPLE),
        ('Épargne',  'savings', savings,                     C_GREEN),
    ]
    for label, key, amount, color in bucket_info:
        real_pct = amount / income * 100 if income else 0
        target   = targets[key]
        gap      = real_pct - target
        gap_color = C_GREEN if abs(gap) <= 5 else (C_RED if gap > 0 else C_ORANGE)
        rule_rows.append([
            Paragraph(f'<font color="{color.hexval()}"><b>{label}</b></font>', S['normal']),
            Paragraph(f'{target:.0f}%', S['normal']),
            Paragraph(f'{real_pct:.1f}%', S['normal']),
            Paragraph(f'<font color="{gap_color.hexval()}">{gap:+.1f}%</font>', S['normal']),
            Paragraph(_fmt(amount), S['normal']),
        ])

    rule_table = Table(rule_rows, colWidths=[90, 50, 55, 55, 80])
    rule_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), C_BORDER),
        ('BACKGROUND', (0,1), (-1,-1), C_SURFACE),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [C_SURFACE, colors.HexColor('#151d2e')]),
        ('BOX', (0,0), (-1,-1), 0.5, C_BORDER),
        ('LINEBELOW', (0,0), (-1,0), 0.5, C_ACCENT),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(rule_table)
    story.append(Spacer(1, 12))

    # ── Top catégories ────────────────────────────────────────────────────────
    story.append(Paragraph("Top dépenses par catégorie", S['h2']))

    top_cats = list(
        qs.filter(type='expense')
        .values('category__name', 'category__icon')
        .annotate(total=Sum('amount'))
        .order_by('-total')[:8]
    )
    if top_cats:
        cat_rows = [[
            Paragraph('<b>#</b>', S['small']), Paragraph('<b>Catégorie</b>', S['small']),
            Paragraph('<b>Montant</b>', S['small']), Paragraph('<b>% revenus</b>', S['small']),
        ]]
        for i, row in enumerate(top_cats, 1):
            pct = float(row['total'] or 0) / income * 100 if income else 0
            cat_rows.append([
                Paragraph(str(i), S['normal']),
                Paragraph(f"{row['category__icon'] or ''} {row['category__name'] or 'Autre'}", S['normal']),
                Paragraph(_fmt(row['total']), S['normal']),
                Paragraph(f"{pct:.1f}%", S['normal']),
            ])
        cat_table = Table(cat_rows, colWidths=[25, 170, 90, 80])
        cat_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), C_BORDER),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [C_SURFACE, colors.HexColor('#151d2e')]),
            ('BOX', (0,0), (-1,-1), 0.5, C_BORDER),
            ('LINEBELOW', (0,0), (-1,0), 0.5, C_ACCENT),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('LEFTPADDING', (0,0), (-1,-1), 8),
        ]))
        story.append(cat_table)
    story.append(Spacer(1, 12))

    # ── Transactions ──────────────────────────────────────────────────────────
    story.append(Paragraph("Transactions du mois", S['h2']))

    txns = qs.select_related('category').order_by('date')
    txn_rows = [[
        Paragraph('<b>Date</b>', S['small']),
        Paragraph('<b>Libellé</b>', S['small']),
        Paragraph('<b>Catégorie</b>', S['small']),
        Paragraph('<b>Montant</b>', S['small']),
    ]]
    for t in txns:
        amount = float(t.amount)
        if t.type == 'income':
            amt_str = f'<font color="{C_GREEN.hexval()}">+{abs(amount):,.0f} €</font>'
        elif t.type == 'saving':
            amt_str = f'<font color="{C_BLUE.hexval()}">{abs(amount):,.0f} €</font>'
        elif amount < 0:
            amt_str = f'<font color="{C_GREEN.hexval()}">+{abs(amount):,.0f} €</font>'
        else:
            amt_str = f'<font color="{C_RED.hexval()}">-{abs(amount):,.0f} €</font>'

        txn_rows.append([
            Paragraph(str(t.date), S['small']),
            Paragraph(t.label[:40], S['normal']),
            Paragraph(t.category.name if t.category else '—', S['small']),
            Paragraph(amt_str, S['normal']),
        ])

    txn_table = Table(txn_rows, colWidths=[55, 175, 90, 70])
    txn_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), C_BORDER),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [C_SURFACE, colors.HexColor('#151d2e')]),
        ('BOX', (0,0), (-1,-1), 0.5, C_BORDER),
        ('LINEBELOW', (0,0), (-1,0), 0.5, C_ACCENT),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(txn_table)

    # ── Footer ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 16))
    story.append(HRFlowable(width='100%', thickness=0.5, color=C_BORDER))
    story.append(Paragraph(f"Généré par Budget Master · {month_label} · {user.username}", S['small']))

    doc.build(story)
    return buf.getvalue()


def _kpi_cell(label, value, color, S):
    return [
        Paragraph(label, S['label']),
        Paragraph(f'<font color="{color.hexval()}">{_fmt(value)}</font>', S['value']),
    ]
