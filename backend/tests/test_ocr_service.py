import unittest

import fitz

from services.ocr_service import ocr_service


class PDFTextFormattingTests(unittest.TestCase):
    def make_pdf(self, page_count: int) -> bytes:
        document = fitz.open()
        page_text = (
            "Invoice number INV-123. Date 2026-10-12. "
            "This digital invoice text is long enough to avoid OCR fallback. "
            "Subtotal 100.00. Tax 18.00. Total 118.00."
        )
        for _ in range(page_count):
            page = document.new_page()
            page.insert_textbox(fitz.Rect(30, 30, 560, 250), page_text)
        return document.tobytes()

    def test_single_page_pdf_has_no_page_banner(self) -> None:
        result = ocr_service.process_pdf(self.make_pdf(1))

        self.assertTrue(result["is_valid"])
        self.assertNotIn("=== PAGE", result["raw_text"])
        self.assertNotIn("Page 1:", result["raw_text"])
        self.assertIn("INV-123", result["raw_text"])

    def test_multi_page_pdf_has_simple_page_labels(self) -> None:
        result = ocr_service.process_pdf(self.make_pdf(2))

        self.assertTrue(result["is_valid"])
        self.assertNotIn("===", result["raw_text"])
        self.assertIn("Page 1:", result["raw_text"])
        self.assertIn("Page 2:", result["raw_text"])


if __name__ == "__main__":
    unittest.main()
