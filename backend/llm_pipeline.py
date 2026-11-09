import os
import json
import requests
from typing import Tuple, Dict, Any, List
from schemas import CreatorExtractionSchema, ReviewerExtractionSchema
from validation import validate_extraction

# Prompts
CREATOR_PROMPT = """You are the CREATOR in a two-stage invoice extraction system.
Your role is to produce the best possible candidate extraction from noisy OCR text.
You are not the final reviewer.
Analyze the complete OCR text carefully.
OCR may contain: spelling mistakes, broken words, incorrect spacing, incorrect characters, missing punctuation, random symbols, incorrect line breaks, confusing layouts.
Use semantic understanding and context.
Extract: vendor_name, invoice_number, date, total_amount, expense_category
For every field provide: value, confidence from 0 to 100, exact OCR evidence supporting the value, a short extraction reason.

RULES:
VENDOR NAME: Identify the company, merchant, restaurant, seller, or organization issuing the document. Do not confuse the vendor with the customer, billing address, shipping address, GST number, or phone number.
INVOICE NUMBER: Look for semantic variants including: Invoice No, Invoice Number, Bill No, Receipt No, Tax Invoice No, Order No, Reference No. Do not confuse GSTIN, PAN, phone numbers, customer IDs, or random numbers with the invoice number.
DATE: Extract the most relevant issue/transaction/invoice date. Do not choose due date unless no issue/transaction date exists. Preserve the original date format unless normalization is explicitly required.
TOTAL AMOUNT: Extract the final payable amount. Prefer: Grand Total, Total Amount, Amount Due, Net Amount, Final Total, Balance Due. Do not select: Subtotal, Tax, Discount, CGST, SGST, VAT, Item Total. If multiple plausible totals exist, select the amount most clearly representing the final payable amount and explain the ambiguity in warnings.
EXPENSE CATEGORY: Choose exactly one allowed category (Meals/Entertainment, Office Supplies, Travel, Software/SaaS, Utilities, Marketing, Miscellaneous). Never invent data. If evidence is weak, use "N/A" and assign low confidence. Do not return N/A simply because OCR labels are imperfect. Perform contextual reasoning before deciding the value is missing.

Return only schema-valid JSON.
"""

REVIEWER_PROMPT = """You are the REVIEWER and FINAL AUTHORITY in a high-accuracy invoice and receipt extraction system.
You receive: Raw OCR text, Cleaned OCR text, Candidate extraction produced by another model.
Your job is to independently verify the candidate against the OCR evidence. Do not trust the candidate automatically.
For every field:
Search the OCR text independently. Inspect the candidate evidence. Decide whether the candidate is supported. Correct the value if a better value exists. Use N/A only when the value genuinely cannot be determined. Prioritize evidence over confidence. A high-confidence candidate without OCR support must be rejected. A low-confidence candidate with strong OCR support may be corrected and accepted.

SPECIAL TOTAL AMOUNT RULE:
When multiple monetary values exist (Grand Total, Final Total, Amount Due, Net Payable) they should generally rank above (Subtotal, Tax, Discount, CGST, SGST, VAT). Never choose a subtotal when a clear final payable amount exists.
SPECIAL INVOICE NUMBER RULE:
Do not mistake GSTIN, PAN, phone numbers, account numbers, customer IDs for invoice numbers unless the OCR explicitly indicates that role.
SPECIAL VENDOR RULE:
The vendor is normally the entity issuing the invoice or receipt. Do not confuse the vendor with buyer, bill-to party, ship-to party, recipient, address block.
EXPENSE CATEGORY RULE:
Return exactly one: Meals/Entertainment, Office Supplies, Travel, Software/SaaS, Utilities, Marketing, Miscellaneous.

FINAL CONFIDENCE:
Calculate field confidence based on OCR evidence strength, label proximity, consistency between Creator and Reviewer, ambiguity.
Confidence guidance:
90-100: Explicit field label and strong OCR evidence.
70-89: Strong contextual evidence with minor OCR noise.
40-69: Plausible but ambiguous.
0-39: Weak evidence.
Never inflate confidence.

Return the final schema only.
"""

def call_openrouter(model: str, system_prompt: str, user_prompt: str, schema_class, retries=1) -> Dict[str, Any]:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY is missing.")

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://opticforge.netlify.app",
        "X-Title": "OpticForge OCR Engine"
    }

    # Generate JSON schema from pydantic model
    schema = schema_class.model_json_schema()

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": schema_class.__name__,
                "strict": True,
                "schema": schema
            }
        }
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=45)
        response.raise_for_status()
        res_data = response.json()
        content = res_data["choices"][0]["message"]["content"].strip()

        # Cleanup markdown if necessary
        if content.startswith("```"):
            import re
            content = re.sub(r"^```(?:json)?", "", content, flags=re.IGNORECASE).strip()
            content = re.sub(r"```$", "", content).strip()

        return json.loads(content)

    except requests.exceptions.RequestException as e:
            # Fallback to json_object if json_schema fails (e.g. 400 Bad Request for unsupported models)
            error_msg = e.response.text if hasattr(e, 'response') and e.response is not None else str(e)
            print(f"OpenRouter API Error: {error_msg}")

            if hasattr(e, 'response') and e.response is not None and e.response.status_code == 400 and retries > 0:
                print("Warning: Structured output might not be supported. Retrying with json_object mode.")
                payload["response_format"] = {"type": "json_object"}

                # Explicitly append schema instruction for json_object fallback
                if "You MUST return a JSON object" not in payload["messages"][0]["content"]:
                    payload["messages"][0]["content"] += f"\n\nYou MUST return a JSON object that strictly follows this schema:\n{json.dumps(schema)}"

                try:
                    response = requests.post(url, headers=headers, json=payload, timeout=45)
                    response.raise_for_status()
                    res_data = response.json()
                    content = res_data["choices"][0]["message"]["content"].strip()

                    if content.startswith("```"):
                        import re
                        content = re.sub(r"^```(?:json)?", "", content, flags=re.IGNORECASE).strip()
                        content = re.sub(r"```$", "", content).strip()

                    return json.loads(content)
                except requests.exceptions.RequestException as e2:
                    error_msg2 = e2.response.text if hasattr(e2, 'response') and e2.response is not None else str(e2)
                    print(f"OpenRouter API Error (json_object mode): {error_msg2}")

                    if hasattr(e2, 'response') and e2.response is not None and e2.response.status_code == 400:
                        print("Warning: json_object not supported either. Retrying without response_format.")
                        if "response_format" in payload:
                            del payload["response_format"]
                        response = requests.post(url, headers=headers, json=payload, timeout=45)
                        response.raise_for_status()
                        res_data = response.json()
                        content = res_data["choices"][0]["message"]["content"].strip()

                        if content.startswith("```"):
                            import re
                            content = re.sub(r"^```(?:json)?", "", content, flags=re.IGNORECASE).strip()
                            content = re.sub(r"```$", "", content).strip()

                        return json.loads(content)
                    else:
                        raise e2
            else:
                raise e

def run_extraction_pipeline(raw_text: str, clean_text: str) -> Tuple[Dict, Dict, List[str]]:
    creator_model = os.getenv("OPENROUTER_CREATOR_MODEL", "google/gemini-2.5-flash")
    reviewer_model = os.getenv("OPENROUTER_REVIEWER_MODEL", "google/gemini-2.5-pro")

    # 1. Creator Phase
    creator_user_prompt = f"Raw OCR Text:\n{raw_text}\n\nCleaned OCR Text:\n{clean_text}"
    creator_output = call_openrouter(creator_model, CREATOR_PROMPT, creator_user_prompt, CreatorExtractionSchema)

    # Validate structure using Pydantic
    creator_validated = CreatorExtractionSchema(**creator_output)

    # 2. Reviewer Phase
    reviewer_user_prompt = f"""
Raw OCR Text:
{raw_text}

Cleaned OCR Text:
{clean_text}

Creator Extraction JSON:
{creator_validated.model_dump_json(indent=2)}
"""
    reviewer_output = call_openrouter(reviewer_model, REVIEWER_PROMPT, reviewer_user_prompt, ReviewerExtractionSchema)
    reviewer_validated = ReviewerExtractionSchema(**reviewer_output)

    # 3. Deterministic Validation Phase
    validation_warnings = validate_extraction(reviewer_validated)

    return creator_validated.model_dump(), reviewer_validated.model_dump(), validation_warnings
