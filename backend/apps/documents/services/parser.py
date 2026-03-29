import re
import hashlib
from datetime import datetime, date
from decimal import Decimal


def parse_file(file_path: str, file_type: str) -> list:
    """
    Parse a PDF or CSV bank statement.
    Returns a list of transaction dicts:
    {date, amount, label, type, suggested_category, confidence, import_hash, is_duplicate}
    """
    if file_type == 'csv':
        return _parse_csv(file_path)
    elif file_type == 'pdf':
        return _parse_pdf(file_path)
    elif file_type == 'xlsx':
        from .excel_parser import parse_excel
        result = parse_excel(file_path)
        # Return only transactions for backward compat; full result via parse_excel_full
        if isinstance(result, dict):
            return result.get('transactions', [])
        return result
    return []


# ── CSV ─────────────────────────────────────────────────────────────────────

def _parse_csv(path: str) -> list:
    import pandas as pd
    transactions = []

    encodings = ['utf-8-sig', 'utf-8', 'latin-1', 'windows-1252', 'iso-8859-1']
    separators = [';', ',', '\t', '|']

    df = None
    for enc in encodings:
        for sep in separators:
            try:
                tmp = pd.read_csv(path, sep=sep, encoding=enc, on_bad_lines='skip')
                if len(tmp.columns) >= 2 and len(tmp) > 0:
                    df = tmp
                    break
            except Exception:
                continue
        if df is not None:
            break

    if df is None:
        return []

    df.columns = [str(c).lower().strip() for c in df.columns]

    # Column detection — broad matching for French and international banks
    date_col = next((c for c in df.columns if re.search(r'date|jour|dat', c)), None)
    label_col = next((c for c in df.columns if re.search(r'libel|label|descr|operat|motif|intitulé|wording', c)), None)
    amount_col = next((c for c in df.columns if re.search(r'montant|amount|somme|valeur|solde', c)), None)
    debit_col = next((c for c in df.columns if re.search(r'debit|débit|retrait|sortie', c)), None)
    credit_col = next((c for c in df.columns if re.search(r'credit|crédit|entrée', c)), None)

    if not date_col or not label_col:
        return []

    for _, row in df.iterrows():
        try:
            label = str(row.get(label_col, '')).strip()
            if not label or label.lower() in ('nan', 'none', ''):
                continue

            parsed_date = _parse_date(str(row.get(date_col, '')).strip())
            if not parsed_date:
                continue

            # Determine amount: prefer separate debit/credit columns
            if debit_col and credit_col:
                debit = _parse_french_amount(str(row.get(debit_col, '') or ''))
                credit = _parse_french_amount(str(row.get(credit_col, '') or ''))
                if credit and credit > 0:
                    amount, is_credit = credit, True
                elif debit and debit > 0:
                    amount, is_credit = debit, False
                else:
                    continue
            elif amount_col:
                raw = str(row.get(amount_col, '0') or '0')
                amount = _parse_french_amount(raw) or 0.0
                is_credit = amount > 0
                amount = abs(amount)
            else:
                continue

            if amount == 0:
                continue

            transactions.append(_make_txn(label, amount, parsed_date, is_credit))
        except Exception:
            continue

    return transactions


# ── PDF dispatcher ───────────────────────────────────────────────────────────

def _parse_pdf(path: str) -> list:
    try:
        import pdfplumber
    except ImportError:
        return []

    try:
        with pdfplumber.open(path) as pdf:
            full_text = '\n'.join(p.extract_text() or '' for p in pdf.pages)
            all_tables = []
            for p in pdf.pages:
                tables = p.extract_tables() or []
                all_tables.extend(tables)
    except Exception:
        return []

    # ── Detect specific bank formats ──────────────────────────────────────
    if re.search(r'BudgetMaster.*Donn.es de seed|Données de seed', full_text, re.I):
        result = _parse_budgetmaster_seed(full_text, all_tables)
        if result:
            return result

    if re.search(r'BNP\s*PARIBAS|RELEVE\s*DE\s*COMPTE\s*CHEQUES', full_text, re.I):
        result = _parse_bnp(full_text)
        if result:
            return result

    if re.search(r'SOCIETE\s*GENERALE|Société\s*Générale', full_text, re.I):
        result = _parse_sg(full_text)
        if result:
            return result

    if re.search(r'CREDIT\s*AGRICOLE|Crédit\s*Agricole', full_text, re.I):
        result = _parse_generic_table(all_tables) or _parse_pdf_generic(full_text)
        if result:
            return result

    if re.search(r'LA\s*BANQUE\s*POSTALE|POSTALE', full_text, re.I):
        result = _parse_generic_table(all_tables) or _parse_pdf_generic(full_text)
        if result:
            return result

    if re.search(r'BOURSORAMA|BOURSO', full_text, re.I):
        result = _parse_generic_table(all_tables) or _parse_pdf_generic(full_text)
        if result:
            return result

    if re.search(r'CIC\b|CRÉDIT\s*MUTUEL|CREDIT\s*MUTUEL', full_text, re.I):
        result = _parse_generic_table(all_tables) or _parse_pdf_generic(full_text)
        if result:
            return result

    # ── Generic: try tables first, then text line scan ────────────────────
    result = _parse_generic_table(all_tables)
    if result:
        return result

    return _parse_pdf_generic(full_text)


# ── BNP Paribas parser ───────────────────────────────────────────────────────

_BNP_CREDIT_KW = re.compile(
    r'VIR(EMENT)?\s*(SCT\s*INST?\s*)?RECU|'
    r'VIR\s*SEPA\s*RECU|'
    r'VIRSCTINSTRECU|'
    r'VIRSEPARECU|'
    r'REMBOURSEMENT|'
    r'SOLDE\s*CREDITEUR',
    re.I
)
_BNP_DEBIT_FORCE_KW = re.compile(
    r'FACTURE|RETRAIT|EMIS|COMMISSION|COTISATION|ECHEANCE|PRELEVEMENT',
    re.I
)
_BNP_LINE_RE = re.compile(
    r'^(\d{2})\.(\d{2})\s+(.+?)\s+\d{2}\.\d{2}\s+([\d ]+,\d{2})\s*$'
)
_BNP_CONT_RE = re.compile(r'^\s{2,}(.+)$')


def _parse_bnp(text: str) -> list:
    year = _detect_year(text)
    transactions = []
    lines = text.split('\n')
    pending = None

    for raw_line in lines:
        m = _BNP_LINE_RE.match(raw_line.strip())
        if m:
            if pending:
                transactions.append(_finalize_bnp(pending, year))
            day       = int(m.group(1))
            month_num = int(m.group(2))
            desc      = m.group(3).strip()
            amount    = float(m.group(4).replace(' ', '').replace(',', '.'))
            pending = {'day': day, 'month': month_num, 'desc': desc, 'amount': amount}
        elif pending and _BNP_CONT_RE.match(raw_line):
            cont = _BNP_CONT_RE.match(raw_line).group(1).strip()
            if not re.match(r'^[A-F0-9]{16,}$|^REFDO|^REFBEN|^NOTPROVIDED', cont, re.I):
                pending['desc'] += ' ' + cont
        else:
            if pending:
                transactions.append(_finalize_bnp(pending, year))
                pending = None

    if pending:
        transactions.append(_finalize_bnp(pending, year))

    return [t for t in transactions if t is not None]


def _finalize_bnp(p: dict, year: int) -> dict | None:
    desc   = p['desc']
    amount = p['amount']
    if re.search(r'SOLDECREDITEUR|TOTAL\s*DES\s*OPER', desc, re.I):
        return None
    try:
        txn_date = date(year, p['month'], p['day'])
    except (ValueError, Exception):
        return None
    is_credit = bool(_BNP_CREDIT_KW.search(desc)) and not bool(_BNP_DEBIT_FORCE_KW.search(desc))
    return _make_txn(_clean_bnp_label(desc), amount, txn_date, is_credit)


def _clean_bnp_label(desc: str) -> str:
    desc = re.sub(r'/REF(DO|BEN)\s*[A-Z0-9]+', '', desc, flags=re.I)
    desc = re.sub(r'/BEN\s+\S+', '', desc, flags=re.I)
    desc = re.sub(r'\b[A-F0-9]{16,}\b', '', desc)
    desc = re.sub(r'\b\d{10,}\b', '', desc)
    desc = re.sub(r'\bDU\d{6}\b', '', desc)
    desc = re.sub(r'FACTURE\(S\)\s*CARTE\s*\d+X+\d+', 'Carte bancaire -', desc, flags=re.I)
    desc = re.sub(r'VIR(EMENT)?\s*SEPA\s*(EMIS|RECU)?', 'Virement', desc, flags=re.I)
    desc = re.sub(r'VIR\s*SCT\s*INST?\s*(EMIS|RECU)?', 'Virement', desc, flags=re.I)
    desc = re.sub(r'VIRSCTINST(EMIS|RECU)', 'Virement', desc, flags=re.I)
    desc = re.sub(r'VIRSEPARECU', 'Virement reçu', desc, flags=re.I)
    desc = re.sub(r'\s{2,}', ' ', desc)
    return desc.strip(' /–-')


# ── Société Générale parser ───────────────────────────────────────────────────

_SG_LINE_RE = re.compile(
    r'(\d{2}/\d{2}/\d{4})\s+(\d{2}/\d{2}/\d{4})\s+(.+?)\s+([-]?[\d\s]+[,\.]\d{2})\s*$'
)

def _parse_sg(text: str) -> list:
    transactions = []
    for line in text.split('\n'):
        m = _SG_LINE_RE.search(line)
        if m:
            try:
                txn_date = datetime.strptime(m.group(1), '%d/%m/%Y').date()
                label    = m.group(3).strip()
                amount   = _parse_french_amount(m.group(4)) or 0.0
                if amount == 0 or not label:
                    continue
                transactions.append(_make_txn(label, abs(amount), txn_date, amount > 0))
            except Exception:
                continue
    return transactions


# ── Generic table parser (pdfplumber extract_tables) ─────────────────────────

def _parse_generic_table(tables: list) -> list:
    """
    Try to extract transactions from PDF tables.
    Looks for rows containing a date, a label, and an amount.
    """
    transactions = []
    date_re = re.compile(
        r'^\d{1,2}[/.\-]\d{1,2}([/.\-]\d{2,4})?$|^\d{4}[/.\-]\d{2}[/.\-]\d{2}$'
    )
    amount_re = re.compile(r'^[-+]?[\d\s]*[,\.]\d{2}\s*[€$]?$')

    for table in tables:
        for row in table:
            if not row:
                continue
            cells = [str(c).strip() if c else '' for c in row]

            # Find date, label, amount columns
            date_idx   = next((i for i, c in enumerate(cells) if date_re.match(c)), None)
            amount_idx = next((i for i, c in enumerate(cells) if amount_re.match(c)), None)

            if date_idx is None or amount_idx is None:
                continue

            # Label: any non-empty cell that's not date or amount
            label_cells = [
                c for i, c in enumerate(cells)
                if i not in (date_idx, amount_idx) and c and not date_re.match(c) and not amount_re.match(c)
            ]
            label = ' '.join(label_cells).strip()
            if not label:
                continue

            parsed_date = _parse_date(cells[date_idx])
            amount = _parse_french_amount(cells[amount_idx])
            if not parsed_date or amount is None or amount == 0:
                continue

            transactions.append(_make_txn(label, abs(amount), parsed_date, amount > 0))

    return transactions


# ── Generic text line parser (fallback) ──────────────────────────────────────

# Matches: date (various formats) + label + amount
_GENERIC_LINE_RE = re.compile(
    r'(\d{1,2}[/.\-]\d{1,2}[/.\-]\d{2,4}|\d{4}[/.\-]\d{2}[/.\-]\d{2})'  # date
    r'\s+'
    r'(.+?)'                                                                  # label
    r'\s+'
    r'([-+]?[\d\s]{1,12}[,\.]\d{2})\s*[€]?'                                # amount
    r'\s*$'
)


def _parse_pdf_generic(text: str) -> list:
    transactions = []
    for line in text.split('\n'):
        m = _GENERIC_LINE_RE.search(line)
        if not m:
            continue
        try:
            raw_date = m.group(1)
            label    = m.group(2).strip()
            amount   = _parse_french_amount(m.group(3))
            if not label or amount is None or amount == 0:
                continue
            parsed_date = _parse_date(raw_date)
            if not parsed_date:
                continue
            transactions.append(_make_txn(label, abs(amount), parsed_date, amount > 0))
        except Exception:
            continue
    return transactions


# ── BudgetMaster seed document parser ────────────────────────────────────────

_FR_MONTHS = {
    'janvier': 1, 'février': 2, 'fevrier': 2, 'mars': 3, 'avril': 4,
    'mai': 5, 'juin': 6, 'juillet': 7, 'août': 8, 'aout': 8,
    'septembre': 9, 'octobre': 10, 'novembre': 11, 'décembre': 12, 'decembre': 12,
}

# Days to use when distributing N occurrences across a month
_OCC_DAYS = {1: [15], 2: [8, 22], 3: [7, 14, 21], 4: [7, 14, 21, 28]}


def _parse_budgetmaster_seed(text: str, tables: list) -> list:
    """
    Parse a BudgetMaster seed specification PDF.
    Generates real transaction records for each month in the stated period.
    """
    import calendar

    # ── 1. Extract period ─────────────────────────────────────────────────
    # "Janvier fi Mars 2025" / "Janvier → Mars 2025" / "Janvier - Mars 2025"
    period_m = re.search(
        r'(janvier|février|fevrier|mars|avril|mai|juin|juillet|août|aout|'
        r'septembre|octobre|novembre|décembre|decembre)'
        r'.{1,6}'
        r'(janvier|février|fevrier|mars|avril|mai|juin|juillet|août|aout|'
        r'septembre|octobre|novembre|décembre|decembre)'
        r'\s+(\d{4})',
        text, re.I
    )
    if not period_m:
        return []

    start_month = _FR_MONTHS.get(period_m.group(1).lower())
    end_month   = _FR_MONTHS.get(period_m.group(2).lower())
    year        = int(period_m.group(3))
    if not start_month or not end_month:
        return []
    months = list(range(start_month, end_month + 1))

    # ── 2. Find the four key tables ───────────────────────────────────────
    revenues, fixed, variables = [], [], []

    for table in tables:
        if not table or len(table) < 2:
            continue
        headers = [str(c).lower().strip() if c else '' for c in table[0]]

        # Revenue table: Source | Montant | Jour
        if any('source' in h for h in headers) and any('jour' in h for h in headers):
            for row in table[1:]:
                if not row or not row[0]:
                    continue
                label = str(row[0]).strip()
                if label.upper() in ('TOTAL', 'SOURCE', ''):
                    continue
                amount = _parse_french_amount(str(row[1])) if len(row) > 1 else None
                day    = _parse_seed_day(str(row[2]) if len(row) > 2 else '1')
                if amount and amount > 0 and label:
                    revenues.append({'label': label, 'amount': amount, 'day': day})

        # Fixed expenses: Libellé | Montant | Catégorie | Jour  — no min/max columns
        elif (any('libel' in h or 'libellé' in h for h in headers)
              and any('catég' in h or 'categ' in h or 'catégorie' in h for h in headers)
              and not any('min' in h for h in headers)):
            for row in table[1:]:
                if not row or not row[0]:
                    continue
                label = str(row[0]).strip()
                if label.upper() in ('TOTAL', 'LIBELLÉ', 'LIBELLE', ''):
                    continue
                amount = _parse_french_amount(str(row[1])) if len(row) > 1 else None
                day    = _parse_seed_day(str(row[3]) if len(row) > 3 else '5')
                if amount and amount > 0 and label:
                    fixed.append({'label': label, 'amount': amount, 'day': day})

        # Variable expenses: Libelle | Min | Max | Catégorie | Occ.
        elif any('min' in h for h in headers) and any('max' in h for h in headers):
            for row in table[1:]:
                if not row or not row[0]:
                    continue
                label = str(row[0]).strip()
                if label.upper() in ('LIBELLE', 'LIBELLÉ', ''):
                    continue
                min_amt = _parse_french_amount(str(row[1])) if len(row) > 1 else None
                max_amt = _parse_french_amount(str(row[2])) if len(row) > 2 else None
                try:
                    occ = int(float(str(row[4]).strip())) if len(row) > 4 else 1
                except (ValueError, TypeError):
                    occ = 1
                if min_amt is not None and max_amt is not None and label:
                    avg = round((min_amt + max_amt) / 2, 2)
                    variables.append({'label': label, 'amount': avg, 'occ': occ})

    if not revenues and not fixed:
        return []

    # ── 3. Generate transactions for each month ───────────────────────────
    transactions = []

    for month in months:
        max_day = calendar.monthrange(year, month)[1]

        # Revenues
        for r in revenues:
            day = min(r['day'], max_day)
            transactions.append(_make_txn(
                r['label'], r['amount'], date(year, month, day), is_credit=True
            ))

        # Fixed expenses
        for f in fixed:
            day = min(f['day'], max_day)
            transactions.append(_make_txn(
                f['label'], f['amount'], date(year, month, day), is_credit=False
            ))

        # Variable expenses — spread occurrences evenly
        for v in variables:
            occ  = min(v['occ'], 4)
            days = _OCC_DAYS.get(occ, [15])
            for d in days:
                d = min(d, max_day)
                transactions.append(_make_txn(
                    v['label'], v['amount'], date(year, month, d), is_credit=False
                ))

    return transactions


def _parse_seed_day(raw: str) -> int:
    """Parse '1er', '3', '5', etc. → integer day."""
    raw = str(raw).strip().lower().replace('er', '').replace('ème', '').replace('eme', '')
    try:
        return max(1, min(28, int(raw)))
    except (ValueError, TypeError):
        return 1


# ── Shared helpers ───────────────────────────────────────────────────────────

def _parse_french_amount(raw: str) -> float | None:
    """
    Parse a French-formatted number string to float.
    Handles: '1 699,00', '-719,00', '1.699,00', '1,699.00' etc.
    """
    if not raw:
        return None
    raw = raw.strip().replace('€', '').replace('\xa0', ' ').strip()
    if not raw or raw.lower() in ('nan', 'none', '-', '–'):
        return None

    # Detect format: if comma before 2 digits at end → French decimal
    if re.search(r',\d{2}$', raw):
        # Remove spaces and dots used as thousands separators
        raw = raw.replace(' ', '').replace('.', '').replace(',', '.')
    else:
        # Assume Anglo format or just clean up
        raw = raw.replace(' ', '').replace(',', '')

    try:
        return float(raw)
    except ValueError:
        return None


def _make_txn(label: str, amount: float, txn_date, is_credit: bool) -> dict:
    from apps.transactions.services.categorization import categorize_label, compute_import_hash
    cat         = categorize_label(label)
    import_hash = compute_import_hash(str(txn_date), str(round(amount, 2)), label)
    return {
        "date":               str(txn_date),
        "amount":             amount,
        "label":              label,
        "type":               "income" if is_credit else "expense",
        "suggested_category": cat['name'] if cat else "Autre",
        "confidence":         cat['confidence'] if cat else 0,
        "import_hash":        import_hash,
        "is_duplicate":       False,
    }


def _detect_year(text: str) -> int:
    m = re.search(r'\bau\s+\d{1,2}\s+\w+\s+(\d{4})\b', text, re.I)
    if m:
        return int(m.group(1))
    m = re.search(r'\b(20\d{2})\b', text)
    if m:
        return int(m.group(1))
    return date.today().year


def _parse_date(raw: str) -> date | None:
    if not raw:
        return None
    raw = raw.strip()
    formats = [
        '%d/%m/%Y', '%d/%m/%y',
        '%Y-%m-%d',
        '%d-%m-%Y', '%d-%m-%y',
        '%d.%m.%Y', '%d.%m.%y',
        '%Y/%m/%d',
        '%d %m %Y',
    ]
    for fmt in formats:
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None
