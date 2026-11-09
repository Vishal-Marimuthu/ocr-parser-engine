import json
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from main import app
from services.llm_service import LLMService


class ExtractionFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        self.fields = {
            "vendor_name": "Acme Supplies",
            "invoice_number": "INV-104",
            "date": "2026-10-12",
            "total_amount": "118.00",
            "expense_category": "Office Supplies",
            "taxable_amount": "100.00",
            "discount_amount": "0",
            "additional_charges": "0.00",
            "tax_inclusive": "no",
            "taxes": [
                {"tax_type": "CGST", "rate": "9%", "amount": "9.00"},
                {"tax_type": "SGST", "rate": "9%", "amount": "9.00"},
            ],
        }

    def test_extract_returns_full_ocr_text_and_ai_fields(self) -> None:
        ocr_text = (
            "Acme Supplies\nInvoice #: INV-104\nDate: 2026-10-12\n"
            "Subtotal: 100.00\nCGST (9%): 9.00\nSGST (9%): 9.00\n"
            "Grand Total: 118.00"
        )
        raw_text = f"\n{ocr_text}\n"
        with (
            patch(
                "api.router.ocr_service.process_image",
                return_value={
                    "raw_text": raw_text,
                    "clean_text": ocr_text,
                    "is_valid": True,
                    "warnings": [],
                },
            ),
            patch(
                "api.router.llm_service.extract_fields",
                new=AsyncMock(return_value=self.fields),
            ) as extract_fields,
        ):
            response = self.client.post(
                "/api/extract",
                files={"file": ("invoice.png", b"image bytes", "image/png")},
            )

        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["extracted_text"], raw_text)
        self.assertEqual(result["data"], self.fields)
        self.assertEqual(result["gst_check"]["tax_status"], "verified")
        self.assertEqual(result["gst_check"]["total_status"], "matches")
        self.assertEqual(result["gst_check"]["calculated_total"], "118.00")
        self.assertEqual(result["extraction_method"], "ai_with_ocr_checks")
        self.assertEqual(result["extraction_warnings"], [])
        extract_fields.assert_awaited_once_with(ocr_text)

    def test_unreadable_document_does_not_call_ai(self) -> None:
        with (
            patch(
                "api.router.ocr_service.process_image",
                return_value={
                    "raw_text": "",
                    "clean_text": "",
                    "is_valid": False,
                    "warnings": ["OCR text is completely empty."],
                },
            ),
            patch("api.router.llm_service.extract_fields", new=AsyncMock()) as extract_fields,
        ):
            response = self.client.post(
                "/api/extract",
                files={"file": ("invoice.png", b"image bytes", "image/png")},
            )

        self.assertEqual(response.status_code, 422)
        self.assertIn("warnings", response.json()["detail"])
        extract_fields.assert_not_awaited()

    def test_ai_failure_uses_visible_local_ocr_fallback(self) -> None:
        with (
            patch(
                "api.router.ocr_service.process_image",
                return_value={
                    "raw_text": "Readable invoice text",
                    "clean_text": "Readable invoice text",
                    "is_valid": True,
                    "warnings": [],
                },
            ),
            patch(
                "api.router.llm_service.extract_fields",
                new=AsyncMock(side_effect=RuntimeError("OpenRouter unavailable")),
            ),
        ):
            response = self.client.post(
                "/api/extract",
                files={"file": ("invoice.png", b"image bytes", "image/png")},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["extraction_method"], "ocr_fallback")
        self.assertTrue(response.json()["extraction_warnings"])
        self.assertEqual(response.json()["data"]["total_amount"], "N/A")

    def test_ai_failure_returns_separate_calculated_invoice_results_per_page(self) -> None:
        text = (
            "Page 1: Tax Invoice For Amazon Seller Services Private Limited: Authorized Signatory\n"
            "Invoice Number : MKT-194629666 Invoice Date : 09.07.2026\n"
            "Tax Amount Total Amount\n1 Marketplace Fees ₹1.27 ₹1.27 "
            "18% IGST ₹0.23 ₹1.50\nTOTAL:\n₹0.23\n₹1.50\n"
            "Amount in Words: One Point Five only\n"
            "Page 2: Tax Invoice For Force24 Lifestyle Private Limited: Authorized Signatory\n"
            "Invoice Number : CJB1-4822 Invoice Date : 09.07.2026\n"
            "Tax Amount Total Amount\n1 Dental Floss ₹176.20 1 ₹176.20 "
            "2.5% CGST ₹4.40 ₹185.00\n2.5% SGST ₹4.40\n"
            "TOTAL:\n₹8.80\n₹185.00\nAmount in Words: One Hundred Eighty-five only\n"
            "Place of delivery: TAMIL NADU"
        )
        with (
            patch(
                "api.router.ocr_service.process_pdf",
                return_value={
                    "raw_text": text,
                    "clean_text": text,
                    "is_valid": True,
                    "warnings": [],
                },
            ),
            patch(
                "api.router.llm_service.extract_fields",
                new=AsyncMock(side_effect=RuntimeError("OpenRouter unavailable")),
            ),
        ):
            response = self.client.post(
                "/api/extract",
                files={"file": ("invoice.pdf", b"pdf bytes", "application/pdf")},
            )

        self.assertEqual(response.status_code, 200)
        invoices = response.json()["invoices"]
        self.assertEqual(len(invoices), 2)
        self.assertEqual(invoices[0]["data"]["invoice_number"], "MKT-194629666")
        self.assertEqual(invoices[0]["data"]["total_amount"], "₹1.50")
        self.assertEqual(invoices[0]["gst_check"]["calculated_total"], "1.50")
        self.assertEqual(invoices[1]["data"]["invoice_number"], "CJB1-4822")
        self.assertEqual(invoices[1]["data"]["additional_charges"], "0.00")
        self.assertEqual(invoices[1]["gst_check"]["calculated_total"], "185.00")
        self.assertEqual(invoices[1]["gst_check"]["recalculated_total"], "185.02")


class OpenRouterRequestTests(unittest.IsolatedAsyncioTestCase):
    async def test_empty_model_response_reports_finish_reason(self) -> None:
        response = MagicMock()
        response.status_code = 200
        response.is_error = False
        response.text = ""
        response.json.return_value = {
            "choices": [{"message": {"content": None}, "finish_reason": "length"}]
        }
        client = AsyncMock()
        client.post.return_value = response

        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
            with self.assertRaisesRegex(RuntimeError, "finish reason: length"):
                await LLMService().call_openrouter(
                    client,
                    "test/model",
                    "Invoice text",
                )

    async def test_default_model_ignores_legacy_creator_model_setting(self) -> None:
        service = LLMService()
        extract_mock = AsyncMock(return_value={
            "vendor_name": "N/A",
            "invoice_number": "N/A",
            "date": "N/A",
            "total_amount": "N/A",
            "expense_category": "N/A",
            "taxable_amount": "N/A",
            "discount_amount": "N/A",
            "additional_charges": "N/A",
            "tax_inclusive": "unknown",
            "taxes": [],
        })

        with (
            patch.dict(
                "os.environ",
                {
                    "OPENROUTER_API_KEY": "test-key",
                    "OPENROUTER_MODEL": "",
                    "OPENROUTER_CREATOR_MODEL": "old/invalid-model:free",
                },
            ),
            patch.object(service, "call_openrouter", new=extract_mock),
        ):
            await service.extract_fields("OCR invoice text")

        self.assertEqual(extract_mock.await_args.args[1], "openrouter/free")

    async def test_extraction_sends_ocr_text_in_one_model_request(self) -> None:
        fields = {
            "vendor_name": "Acme Supplies",
            "invoice_number": "INV-104",
            "date": "2026-10-12",
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
        response = MagicMock()
        response.status_code = 200
        response.is_error = False
        response.text = ""
        response.json.return_value = {
            "choices": [{"message": {"content": json.dumps(fields)}}]
        }
        client = AsyncMock()
        client.__aenter__.return_value = client
        client.post.return_value = response

        with (
            patch.dict(
                "os.environ",
                {
                    "OPENROUTER_API_KEY": "test-key",
                    "OPENROUTER_MODEL": "test/model",
                },
            ),
            patch("services.llm_service.httpx.AsyncClient", return_value=client),
        ):
            result = await LLMService().extract_fields("OCR invoice text")

        self.assertEqual(result, fields)
        client.post.assert_awaited_once()
        request = client.post.await_args.kwargs["json"]
        self.assertEqual(request["model"], "test/model")
        self.assertIn("OCR invoice text", request["messages"][1]["content"])
        self.assertEqual(request["response_format"]["type"], "json_object")
        self.assertIn("Return a JSON object matching this schema", request["messages"][0]["content"])
        self.assertEqual(request["max_tokens"], 1200)


if __name__ == "__main__":
    unittest.main()
