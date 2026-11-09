import unittest
from pathlib import Path

from services.local_extraction_service import local_extraction_service
from services.local_extraction_service import split_invoice_pages
from services.tax_service import calculate_gst


class LocalExtractionTests(unittest.TestCase):
    def test_extracts_flattened_invoice_tables_separately_by_page(self) -> None:
        text = (
            "Page 1: Tax Invoice For Amazon Seller Services Private Limited: Authorized Signatory "
            "Invoice Number : MKT-194629666 Order Date: 05.07.2026 Invoice Date : 09.07.2026 "
            "Sl. No Description Unit Price Qty Net Amount Tax Rate Tax Type Tax Amount Total Amount "
            "1 Marketplace Fees ₹1.27 ₹1.27 18% IGST ₹0.23 ₹1.50 "
            "TOTAL:\n₹0.23\n₹1.50\nAmount in Words: One Point Five only "
            "Invoice Value: 1.50 "
            "Page 2: Tax Invoice For Force24 Lifestyle Private Limited: Authorized Signatory "
            "Invoice Number : CJB1-4822 Order Date: 05.07.2026 Invoice Date : 09.07.2026 "
            "Sl. No Description Unit Price Qty Net Amount Tax Rate Tax Type Tax Amount Total Amount "
            "1 Dental Floss ₹176.20 1 ₹176.20 2.5% CGST ₹4.40 ₹185.00 "
            "2.5% SGST ₹4.40 TOTAL: ₹8.80 ₹185.00"
        )
        pages = split_invoice_pages(text)

        self.assertEqual([number for number, _ in pages], [1, 2])
        first = local_extraction_service.extract_fields(pages[0][1])
        second = local_extraction_service.extract_fields(pages[1][1])
        first_check = calculate_gst(first)
        second_check = calculate_gst(second)

        self.assertEqual(first.vendor_name, "Amazon Seller Services Private Limited")
        self.assertEqual(first.invoice_number, "MKT-194629666")
        self.assertEqual(first.date, "09.07.2026")
        self.assertEqual(first.taxable_amount, "₹1.27")
        self.assertEqual(first.taxes[0].tax_type, "IGST")
        self.assertEqual(first.taxes[0].amount, "₹0.23")
        self.assertEqual(first.total_amount, "₹1.50")
        self.assertEqual(first_check.taxes[0].calculated_amount, "0.23")
        self.assertEqual(first_check.calculated_total, "1.50")
        self.assertEqual(first_check.total_status, "matches")

        self.assertEqual(second.vendor_name, "Force24 Lifestyle Private Limited")
        self.assertEqual(second.invoice_number, "CJB1-4822")
        self.assertEqual(second.date, "09.07.2026")
        self.assertEqual(second.taxable_amount, "₹176.20")
        self.assertEqual([tax.amount for tax in second.taxes], ["₹4.40", "₹4.40"])
        self.assertEqual(second.total_amount, "₹185.00")
        self.assertEqual([tax.calculated_amount for tax in second_check.taxes], ["4.41", "4.41"])
        self.assertEqual(second_check.calculated_total, "185.00")
        self.assertEqual(second_check.total_difference, "0.00")
        self.assertEqual(second_check.total_status, "matches")
        self.assertEqual(second_check.calculated_gst_total, "8.82")
        self.assertEqual(second_check.recalculated_total, "185.02")
        self.assertEqual(second_check.recalculated_difference, "-0.02")
        self.assertEqual(second_check.recalculated_total_status, "rounding_difference")

    def test_handles_total_on_following_lines_and_ignores_delivery_address(self) -> None:
        rupee = "\u20b9"
        text = (
            "For Force24 Lifestyle Private Limited: Authorized Signatory\n"
            "Invoice Number: CJB1-4822\n"
            "Invoice Date: 09.07.2026\n"
            "Tax Amount Total Amount\n"
            f"1 Dental Floss {rupee}176.20 1 {rupee}176.20 "
            f"2.5% CGST {rupee}4.40 {rupee}185.00\n"
            f"2.5% SGST {rupee}4.40\n"
            "TOTAL:\n"
            f"{rupee}8.80\n"
            f"{rupee}185.00\n"
            "Amount in Words: One Hundred Eighty-five only\n"
            "Place of delivery: TAMIL NADU"
        )

        fields = local_extraction_service.extract_fields(text)
        check = calculate_gst(fields)

        self.assertEqual(fields.total_amount, f"{rupee}185.00")
        self.assertEqual(fields.additional_charges, "0.00")
        self.assertEqual(check.calculated_total, "185.00")
        self.assertEqual(check.total_status, "matches")
        self.assertEqual(check.recalculated_total, "185.02")
        self.assertEqual(check.recalculated_total_status, "rounding_difference")

    def test_extracts_explicit_delivery_charge_amount(self) -> None:
        fields = local_extraction_service.extract_fields(
            "Subtotal: 100.00\nShipping charges: 5.00\n"
            "Tax (10%): 10.00\nGrand Total: 115.00"
        )

        self.assertEqual(fields.additional_charges, "5.00")

    def test_extracts_and_calculates_sample_invoice_five_times(self) -> None:
        image_path = Path(__file__).parents[2] / "frontend" / "public" / "sample_invoice.png"
        from services.ocr_service import ocr_service

        for _ in range(5):
            ocr = ocr_service.process_image(image_path.read_bytes())
            fields = local_extraction_service.extract_fields(ocr["clean_text"])
            check = calculate_gst(fields)

            self.assertEqual(fields.vendor_name, "ACME Corporation")
            self.assertEqual(fields.invoice_number, "INV9875")
            self.assertEqual(fields.taxable_amount, "$4,050.50")
            self.assertEqual(fields.taxes[0].tax_type, "Tax")
            self.assertEqual(fields.taxes[0].rate, "8%")
            self.assertEqual(fields.taxes[0].amount, "$324.04")
            self.assertEqual(fields.total_amount, "874.54")
            self.assertEqual(check.taxes[0].calculated_amount, "324.04")
            self.assertEqual(check.taxes[0].status, "matches")
            self.assertEqual(check.calculated_total, "4374.54")
            self.assertEqual(check.total_status, "mismatch")


if __name__ == "__main__":
    unittest.main()
