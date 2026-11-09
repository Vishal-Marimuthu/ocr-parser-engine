import unittest

from schemas import DocumentFields
from services.tax_service import calculate_gst


def invoice_fields(**overrides: object) -> DocumentFields:
    values: dict[str, object] = {
        "vendor_name": "Test vendor",
        "invoice_number": "INV-1",
        "date": "2026-01-01",
        "total_amount": "118.00",
        "expense_category": "Office Supplies",
        "taxable_amount": "100.00",
        "discount_amount": "0",
        "additional_charges": "0",
        "tax_inclusive": "no",
        "taxes": [
            {"tax_type": "CGST", "rate": "9%", "amount": "9.00"},
            {"tax_type": "SGST", "rate": "9%", "amount": "9.00"},
        ],
    }
    values.update(overrides)
    return DocumentFields.model_validate(values)


class GSTCalculationTests(unittest.TestCase):
    def test_calculates_each_gst_component_and_total(self) -> None:
        result = calculate_gst(invoice_fields())

        self.assertEqual(result.tax_status, "verified")
        self.assertEqual(result.total_status, "matches")
        self.assertEqual(result.gst_total, "18.00")
        self.assertEqual(result.calculated_total, "118.00")
        self.assertEqual([tax.calculated_amount for tax in result.taxes], ["9.00", "9.00"])

    def test_flags_wrong_gst_and_invoice_total(self) -> None:
        fields = invoice_fields(
            total_amount="123.45",
            taxes=[
                {"tax_type": "IGST", "rate": "18%", "amount": "20.00"},
            ],
        )

        result = calculate_gst(fields)

        self.assertEqual(result.tax_status, "mismatch")
        self.assertEqual(result.total_status, "mismatch")
        self.assertEqual(result.taxes[0].calculated_amount, "18.00")
        self.assertEqual(result.calculated_total, "120.00")
        self.assertEqual(result.total_difference, "3.45")

    def test_reports_small_currency_rounding_difference(self) -> None:
        fields = invoice_fields(
            total_amount="118.02",
            taxes=[{"tax_type": "GST", "rate": "18%", "amount": "18.01"}],
        )

        result = calculate_gst(fields)

        self.assertEqual(result.tax_status, "rounding_difference")
        self.assertEqual(result.total_status, "rounding_difference")
        self.assertEqual(result.taxes[0].status, "rounding_difference")

    def test_inclusive_invoice_does_not_add_tax_twice(self) -> None:
        result = calculate_gst(
            invoice_fields(tax_inclusive="yes", total_amount="118.00")
        )

        self.assertEqual(result.tax_status, "verified")
        self.assertEqual(result.total_status, "tax_inclusive")
        self.assertEqual(result.calculated_total, "N/A")

    def test_unclear_tax_treatment_does_not_guess_invoice_total(self) -> None:
        result = calculate_gst(
            invoice_fields(tax_inclusive="unknown")
        )

        self.assertEqual(result.total_status, "incomplete")
        self.assertEqual(result.calculated_total, "N/A")

    def test_no_gst_and_other_tax_are_reported_separately(self) -> None:
        result = calculate_gst(
            invoice_fields(
                total_amount="108.00",
                taxes=[{"tax_type": "Sales tax", "rate": "8%", "amount": "8.00"}],
            )
        )

        self.assertEqual(result.tax_status, "no_gst")
        self.assertEqual(result.gst_total, "0.00")
        self.assertEqual(result.other_tax_total, "8.00")
        self.assertEqual(result.calculated_total, "108.00")
        self.assertEqual(result.taxes[0].calculated_amount, "8.00")
        self.assertEqual(result.taxes[0].status, "matches")

    def test_cannot_verify_missing_taxable_amount_or_tax_rate(self) -> None:
        missing_base = calculate_gst(invoice_fields(taxable_amount="N/A"))
        missing_rate = calculate_gst(
            invoice_fields(taxes=[{"tax_type": "CGST", "rate": "N/A", "amount": "9.00"}])
        )

        self.assertEqual(missing_base.tax_status, "incomplete")
        self.assertEqual(missing_rate.tax_status, "incomplete")

    def test_discount_is_informational_and_additional_charge_is_added_once(self) -> None:
        result = calculate_gst(
            invoice_fields(
                total_amount="113.00",
                taxable_amount="100.00",
                discount_amount="10.00",
                additional_charges="5.00",
                taxes=[{"tax_type": "GST", "rate": "8%", "amount": "8.00"}],
            )
        )

        self.assertEqual(result.total_status, "matches")
        self.assertEqual(result.calculated_total, "113.00")

    def test_currency_symbols_thousands_separators_and_rounding(self) -> None:
        fields = invoice_fields(
            total_amount="₹1,180.00",
            taxable_amount="Rs. 1,000.00",
            additional_charges="0",
            taxes=[
                {"tax_type": "CGST", "rate": "9%", "amount": "₹90.00"},
                {"tax_type": "SGST", "rate": "9%", "amount": "₹90.00"},
            ],
        )

        result = calculate_gst(fields)

        self.assertEqual(result.tax_status, "verified")
        self.assertEqual(result.total_status, "matches")
        self.assertEqual(result.calculated_total, "1180.00")


if __name__ == "__main__":
    unittest.main()
