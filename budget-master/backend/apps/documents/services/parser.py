import csv
import io
from datetime import datetime
from apps.transactions.services.categorization import auto_categorize, compute_import_hash


def parse_csv(file_content, user):
    """Parse a CSV bank statement and return list of transaction dicts."""
    transactions = []

    try:
        content = file_content.decode('utf-8-sig')
    except UnicodeDecodeError:
        content = file_content.decode('latin-1')

    reader = csv.DictReader(io.StringIO(content), delimiter=';')

    for row in reader:
        try:
            # Try common CSV formats
            date_str = row.get('date') or row.get('Date') or row.get('DATE') or ''
            amount_str = row.get('amount') or row.get('Amount') or row.get('montant') or row.get('Montant') or ''
            label = row.get('label') or row.get('Label') or row.get('libelle') or row.get('Libellé') or row.get('description') or ''

            if not date_str or not amount_str or not label:
                continue

            # Parse date
            for fmt in ['%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%m/%d/%Y']:
                try:
                    parsed_date = datetime.strptime(date_str.strip(), fmt).date()
                    break
                except ValueError:
                    continue
            else:
                continue

            # Parse amount
            amount_clean = amount_str.replace(' ', '').replace(',', '.').replace('€', '').strip()
            amount = float(amount_clean)

            # Determine transaction type
            if amount > 0:
                t_type = 'income'
            else:
                t_type = 'expense'
                amount = abs(amount)

            # Auto-categorize
            cat_name, confidence = auto_categorize(label, user)

            # Import hash
            import_hash = compute_import_hash(parsed_date, amount, label)

            transactions.append({
                'date': parsed_date,
                'amount': amount,
                'label': label.strip(),
                'type': t_type,
                'category_name': cat_name,
                'confidence': confidence,
                'import_hash': import_hash,
                'source': 'import',
            })
        except (ValueError, KeyError):
            continue

    return transactions


def parse_pdf(file_path, user):
    """Parse a PDF bank statement."""
    try:
        import pdfplumber
        transactions = []

        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ''
                lines = text.split('\n')
                for line in lines:
                    parts = line.strip().split()
                    if len(parts) < 3:
                        continue
                    # Try to find date pattern
                    try:
                        date_str = parts[0]
                        parsed_date = datetime.strptime(date_str, '%d/%m/%Y').date()
                        # Try to find amount (last numeric field)
                        amount_str = parts[-1].replace(',', '.').replace(' ', '')
                        amount = abs(float(amount_str))
                        label = ' '.join(parts[1:-1])

                        t_type = 'income' if float(parts[-1].replace(',', '.')) > 0 else 'expense'
                        cat_name, confidence = auto_categorize(label, user)
                        import_hash = compute_import_hash(parsed_date, amount, label)

                        transactions.append({
                            'date': parsed_date,
                            'amount': amount,
                            'label': label,
                            'type': t_type,
                            'category_name': cat_name,
                            'confidence': confidence,
                            'import_hash': import_hash,
                            'source': 'import',
                        })
                    except (ValueError, IndexError):
                        continue

        return transactions
    except ImportError:
        return []
