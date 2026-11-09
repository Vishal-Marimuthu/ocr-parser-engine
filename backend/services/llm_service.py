import json
import os
import re
from typing import Any

import httpx

from schemas import DocumentFields


EXTRACTION_PROMPT = """Extract these fields from the supplied OCR text:
vendor_name, invoice_number, date, total_amount, expense_category,
taxable_amount, discount_amount, additional_charges, tax_inclusive, taxes.

Return only a JSON object matching the provided schema.
total_amount is the final amount printed as due, not the subtotal or tax.
taxable_amount is the net taxable base after discounts and before taxes.
discount_amount is informational; do not subtract it from taxable_amount again.
additional_charges includes only non-tax charges excluded from taxable_amount and
the listed taxes; use "0" when none are listed, and do not count a charge twice.
tax_inclusive must be "yes" only when the document clearly says tax is included,
"no" when it clearly shows tax added to a pre-tax taxable amount, otherwise "unknown".
List every distinct tax component with its printed type, rate, and amount. If CGST
and SGST (or IGST) are shown, do not add a duplicate aggregate GST summary line.
Use "N/A" for an unreadable or absent scalar value. Use an empty taxes array when
no tax is shown. Never invent or calculate amounts; calculations are performed by
the API. For expense_category, choose exactly one of: Meals/Entertainment,
Office Supplies, Travel, Software/SaaS, Utilities, Marketing, Miscellaneous."""


class LLMService:
    async def call_openrouter(
        self,
        client: httpx.AsyncClient,
        model: str,
        extracted_text: str,
    ) -> dict[str, Any]:
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY is missing.")

        schema = DocumentFields.model_json_schema()
        payload: dict[str, Any] = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        f"{EXTRACTION_PROMPT}\n"
                        "Return a JSON object matching this schema:\n"
                        f"{json.dumps(schema)}"
                    ),
                },
                {"role": "user", "content": f"OCR text:\n{extracted_text}"},
            ],
            "response_format": {"type": "json_object"},
            "max_tokens": 1200,
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://opticforge.netlify.app",
            "X-Title": "OpticForge OCR Engine",
        }

        response = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=60.0,
        )
        if response.is_error:
            raise RuntimeError(
                f"OpenRouter request failed with HTTP {response.status_code}: "
                f"{response.text[:500]}"
            )
        response_data = response.json()
        choices = response_data.get("choices") if isinstance(response_data, dict) else None
        if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
            raise RuntimeError("OpenRouter returned no extraction choices.")
        choice = choices[0]
        message = choice.get("message")
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError(
                "OpenRouter returned no extraction text "
                f"(finish reason: {choice.get('finish_reason', 'unknown')})."
            )
        content = content.strip()
        content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content, flags=re.IGNORECASE)
        return json.loads(content)

    async def extract_fields(self, extracted_text: str) -> dict[str, str]:
        model = os.getenv("OPENROUTER_MODEL") or "openrouter/free"
        async with httpx.AsyncClient() as client:
            result = await self.call_openrouter(client, model, extracted_text)
        return DocumentFields.model_validate(result).model_dump()


llm_service = LLMService()
