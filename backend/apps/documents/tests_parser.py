"""
Tests unitaires — parser.py (documents/services/parser.py)
"""
import os
import tempfile
from django.test import TestCase


class ParserHelpersTest(TestCase):

    def test_parse_french_amount_comma(self):
        from apps.documents.services.parser import _parse_french_amount
        self.assertAlmostEqual(_parse_french_amount('1 699,00'), 1699.0)
        self.assertAlmostEqual(_parse_french_amount('-719,00'), -719.0)
        self.assertAlmostEqual(_parse_french_amount('50,00'), 50.0)

    def test_parse_french_amount_dot(self):
        from apps.documents.services.parser import _parse_french_amount
        self.assertAlmostEqual(_parse_french_amount('1699.00'), 1699.0)
        self.assertAlmostEqual(_parse_french_amount('-719.00'), -719.0)

    def test_parse_french_amount_none_on_invalid(self):
        from apps.documents.services.parser import _parse_french_amount
        self.assertIsNone(_parse_french_amount(''))
        self.assertIsNone(_parse_french_amount('N/A'))
        self.assertIsNone(_parse_french_amount(None))

    def test_parse_csv_basic(self):
        """Simple CSV with Date;Libellé;Montant columns should produce transactions."""
        from apps.documents.services.parser import parse_file

        csv_content = (
            "Date;Libellé;Montant\n"
            "01/01/2025;Salaire;1699,00\n"
            "05/01/2025;Loyer;-719,00\n"
            "10/01/2025;Courses;-58,00\n"
        )

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            f.write(csv_content)
            tmp_path = f.name

        try:
            result = parse_file(tmp_path, 'csv')
        finally:
            os.unlink(tmp_path)

        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0, "CSV parser returned no transactions")
        for txn in result:
            self.assertIn('date', txn)
            self.assertIn('label', txn)
            self.assertIn('amount', txn)

    def test_parse_csv_transaction_keys(self):
        """Each transaction from CSV must have import_hash and suggested_category."""
        from apps.documents.services.parser import parse_file

        csv_content = (
            "Date;Libellé;Montant\n"
            "01/03/2025;Virement salaire;2000,00\n"
        )

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            f.write(csv_content)
            tmp_path = f.name

        try:
            result = parse_file(tmp_path, 'csv')
        finally:
            os.unlink(tmp_path)

        if result:
            txn = result[0]
            self.assertIn('import_hash', txn)
            self.assertIn('suggested_category', txn)
            self.assertIn('is_duplicate', txn)

    def test_parse_csv_debit_credit_columns(self):
        """CSV with separate Débit/Crédit columns."""
        from apps.documents.services.parser import parse_file

        csv_content = (
            "Date;Libellé;Débit;Crédit\n"
            "01/01/2025;Salaire;;1699,00\n"
            "05/01/2025;Loyer;719,00;\n"
        )

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            f.write(csv_content)
            tmp_path = f.name

        try:
            result = parse_file(tmp_path, 'csv')
        finally:
            os.unlink(tmp_path)

        self.assertIsInstance(result, list)
        if result:
            amounts = [t['amount'] for t in result]
            self.assertTrue(any(a > 0 for a in amounts), "No positive amount found (salary)")
