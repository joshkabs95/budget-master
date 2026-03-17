import re
import hashlib
from datetime import datetime
from decimal import Decimal


def parse_file(file_path: str, file_type: str) -> list:
    """
    Parse a PDF or CSV bank statement file.
    Returns a list of transaction dicts:
    {date, amount, label, suggested_category, import_hash}
    """
    if file_type == 'csv':
        return _parse_csv(file_path)
    elif file_type == 'pdf':
        return _parse_pdf(file_path)
    return []


def _parse_csv(path: str) -> list:
    import pandas as pd

    transactions = []
    try:
        # Try common French bank CSV formats
        for sep in [';', ',', '\t']:
            try:
                df = pd.read_csv(path, sep=sep, encoding='utf-8-sig')
                if len(df.columns) >= 3:
                    break
            except Exception:
                continue

        # Normalize column names
        df.columns = [c.lower().strip() for c in df.columns]

        date_col = next((c for c in df.columns if 'date' in c), None)
        amount_col = next((c for c in df.columns if any(k in c for k in ['montant', 'amount', 'debit', 'credit', 'somme'])), None)
        label_col = next((c for c in df.columns if any(k in c for k in ['libelle', 'label', 'description', 'operation'])), None)

        if not all([date_col, label_col]):
            return []

        for _, row in df.iterrows():
            try:
                label = str(row.get(label_col, '')).strip()
                raw_amount = str(row.get(amount_col, '0')).replace(',', '.').replace(' ', '')
                amount = float(re.sub(r'[^\d.\-]', '', raw_amount) or '0')
                raw_date = str(row.get(date_col, '')).strip()
                parsed_date = _parse_date(raw_date)

                if not parsed_date or not label:
                    continue

                from apps.transactions.services.categorization import categorize_label, compute_import_hash
                cat = categorize_label(label)
                import_hash = compute_import_hash(str(parsed_date), str(abs(amount)), label)

                transactions.append({
                    "date": str(parsed_date),
                    "amount": abs(amount),
                    "label": label,
                    "type": "income" if amount > 0 else "expense",
                    "suggested_category": cat['name'] if cat else "Autre",
                    "confidence": cat['confidence'] if cat else 0,
                    "import_hash": import_hash,
                })
            except Exception:
                continue

    except Exception as e:
        pass

    return transactions


def _parse_pdf(path: str) -> list:
    try:
        import pdfplumber
    except ImportError:
        return []

    transactions = []
    try:
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ''
                lines = text.split('\n')

                for line in lines:
                    # French bank PDF pattern: DD/MM/YYYY ... description ... amount
                    match = re.search(
                        r'(\d{2}/\d{2}/\d{4})\s+(.+?)\s+([-]?\d[\d\s]*[,\.]\d{2})',
                        line
                    )
                    if match:
                        try:
                            raw_date = match.group(1)
                            label = match.group(2).strip()
                            raw_amount = match.group(3).replace(' ', '').replace(',', '.')
                            amount = float(raw_amount)
                            parsed_date = datetime.strptime(raw_date, '%d/%m/%Y').date()

                            from apps.transactions.services.categorization import categorize_label, compute_import_hash
                            cat = categorize_label(label)
                            import_hash = compute_import_hash(str(parsed_date), str(abs(amount)), label)

                            transactions.append({
                                "date": str(parsed_date),
                                "amount": abs(amount),
                                "label": label,
                                "type": "income" if amount > 0 else "expense",
                                "suggested_category": cat['name'] if cat else "Autre",
                                "confidence": cat['confidence'] if cat else 0,
                                "import_hash": import_hash,
                            })
                        except Exception:
                            continue
    except Exception:
        pass

    return transactions


def _parse_date(raw: str):
    formats = ['%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%d.%m.%Y', '%Y/%m/%d']
    for fmt in formats:
        try:
            return datetime.strptime(raw.strip(), fmt).date()
        except ValueError:
            continue
    return None
