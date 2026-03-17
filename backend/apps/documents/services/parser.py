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
    return []


# ── CSV ─────────────────────────────────────────────────────────────────────

def _parse_csv(path: str) -> list:
    import pandas as pd
    transactions = []
    try:
        df = None
        for sep in [';', ',', '\t']:
            try:
                tmp = pd.read_csv(path, sep=sep, encoding='utf-8-sig')
                if len(tmp.columns) >= 3:
                    df = tmp
                    break
            except Exception:
                continue
        if df is None:
            return []

        df.columns = [c.lower().strip() for c in df.columns]
        date_col   = next((c for c in df.columns if 'date' in c), None)
        amount_col = next((c for c in df.columns if any(k in c for k in ['montant', 'amount', 'debit', 'credit', 'somme'])), None)
        label_col  = next((c for c in df.columns if any(k in c for k in ['libelle', 'label', 'description', 'operation'])), None)

        if not all([date_col, label_col]):
            return []

        for _, row in df.iterrows():
            try:
                label      = str(row.get(label_col, '')).strip()
                raw_amount = str(row.get(amount_col, '0')).replace(',', '.').replace(' ', '')
                amount     = float(re.sub(r'[^\d.\-]', '', raw_amount) or '0')
                parsed_date = _parse_date(str(row.get(date_col, '')).strip())
                if not parsed_date or not label:
                    continue
                transactions.append(_make_txn(label, abs(amount), parsed_date, amount > 0))
            except Exception:
                continue
    except Exception:
        pass
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
    except Exception:
        return []

    # Detect bank format
    if re.search(r'BNP\s*PARIBAS|RELEVE\s*DE\s*COMPTE\s*CHEQUES', full_text, re.I):
        return _parse_bnp(full_text)

    # Generic fallback: look for DD/MM/YYYY ... amount
    return _parse_pdf_generic(full_text)


# ── BNP Paribas parser ───────────────────────────────────────────────────────

# Keywords that mark an incoming transfer (credit)
_BNP_CREDIT_KW = re.compile(
    r'VIR(EMENT)?\s*(SCT\s*INST?\s*)?RECU|'
    r'VIR\s*SEPA\s*RECU|'
    r'VIRSCTINSTRECU|'
    r'VIRSEPARECU|'
    r'REMBOURSEMENT|'
    r'SOLDE\s*CREDITEUR',
    re.I
)

# Keywords that always make it a debit even if "RECU" substring appears somewhere
_BNP_DEBIT_FORCE_KW = re.compile(
    r'FACTURE|RETRAIT|EMIS|COMMISSION|COTISATION|ECHEANCE|PRELEVEMENT',
    re.I
)

# BNP transaction line: starts DD.MM, ends with a Euro amount (may have spaces inside)
# e.g.  "02.02 VIRSCTINSTRECU/DEJOSUE  02.02 1798,88"
_BNP_LINE_RE = re.compile(
    r'^(\d{2})\.(\d{2})\s+(.+?)\s+\d{2}\.\d{2}\s+([\d ]+,\d{2})\s*$'
)

# Continuation lines after the first line of an operation (no date prefix)
# Used to concatenate multi-line labels
_BNP_CONT_RE = re.compile(r'^\s{2,}(.+)$')


def _parse_bnp(text: str) -> list:
    """
    Parse a BNP Paribas bank statement.
    Handles the French DD.MM format and implicit year from document header.
    """
    # Detect statement year from header "au 28 février 2026"
    year = _detect_year(text)

    transactions = []
    lines = text.split('\n')
    pending: dict | None = None  # current multi-line operation being assembled

    for raw_line in lines:
        m = _BNP_LINE_RE.match(raw_line.strip())

        if m:
            # Flush previous pending transaction
            if pending:
                transactions.append(_finalize_bnp(pending, year))

            day        = int(m.group(1))
            month_num  = int(m.group(2))
            desc       = m.group(3).strip()
            amount_str = m.group(4).replace(' ', '').replace(',', '.')
            amount     = float(amount_str)
            pending = {'day': day, 'month': month_num, 'desc': desc, 'amount': amount}

        elif pending and _BNP_CONT_RE.match(raw_line):
            # Continuation of previous operation label
            cont = _BNP_CONT_RE.match(raw_line).group(1).strip()
            # Skip technical reference lines (long hex strings, ref numbers)
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
    day    = p['day']
    month  = p['month']

    # Skip balance lines and totals (not individual commission transactions)
    if re.search(r'SOLDECREDITEUR|TOTAL\s*DES\s*OPER', desc, re.I):
        return None

    try:
        # Handle cross-year (e.g. December transaction in January statement)
        try:
            txn_date = date(year, month, day)
        except ValueError:
            return None
    except Exception:
        return None

    # Determine credit vs debit
    is_credit = bool(_BNP_CREDIT_KW.search(desc)) and not bool(_BNP_DEBIT_FORCE_KW.search(desc))

    return _make_txn(_clean_bnp_label(desc), amount, txn_date, is_credit)


def _clean_bnp_label(desc: str) -> str:
    """Remove BNP noise from operation descriptions."""
    # Remove technical patterns
    desc = re.sub(r'/REF(DO|BEN)\s*[A-Z0-9]+', '', desc, flags=re.I)
    desc = re.sub(r'/BEN\s+\S+', '', desc, flags=re.I)
    desc = re.sub(r'\b[A-F0-9]{16,}\b', '', desc)        # hex references
    desc = re.sub(r'\b\d{10,}\b', '', desc)               # long digit strings
    desc = re.sub(r'\bDU\d{6}\b', '', desc)               # DU060226 etc.
    desc = re.sub(r'FACTURE\(S\)\s*CARTE\s*\d+X+\d+', 'Carte bancaire -', desc, flags=re.I)
    desc = re.sub(r'VIR(EMENT)?\s*SEPA\s*(EMIS|RECU)?', 'Virement', desc, flags=re.I)
    desc = re.sub(r'VIR\s*SCT\s*INST?\s*(EMIS|RECU)?', 'Virement', desc, flags=re.I)
    desc = re.sub(r'VIRSCTINST(EMIS|RECU)', 'Virement', desc, flags=re.I)
    desc = re.sub(r'VIRSEPARECU', 'Virement reçu', desc, flags=re.I)
    desc = re.sub(r'\s{2,}', ' ', desc)
    return desc.strip(' /–-')


def _detect_year(text: str) -> int:
    m = re.search(r'\bau\s+\d{1,2}\s+\w+\s+(\d{4})\b', text, re.I)
    if m:
        return int(m.group(1))
    m = re.search(r'\b(20\d{2})\b', text)
    if m:
        return int(m.group(1))
    return date.today().year


# ── Generic PDF parser ───────────────────────────────────────────────────────

def _parse_pdf_generic(text: str) -> list:
    transactions = []
    for line in text.split('\n'):
        m = re.search(
            r'(\d{2}/\d{2}/\d{4})\s+(.+?)\s+([-]?\d[\d\s]*[,\.]\d{2})',
            line
        )
        if m:
            try:
                raw_date = m.group(1)
                label    = m.group(2).strip()
                amount   = float(m.group(3).replace(' ', '').replace(',', '.'))
                txn_date = datetime.strptime(raw_date, '%d/%m/%Y').date()
                transactions.append(_make_txn(label, abs(amount), txn_date, amount > 0))
            except Exception:
                continue
    return transactions


# ── Shared helpers ───────────────────────────────────────────────────────────

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
        "is_duplicate":       False,  # set by the view
    }


def _parse_date(raw: str):
    for fmt in ['%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%d.%m.%Y', '%Y/%m/%d']:
        try:
            return datetime.strptime(raw.strip(), fmt).date()
        except ValueError:
            continue
    return None
