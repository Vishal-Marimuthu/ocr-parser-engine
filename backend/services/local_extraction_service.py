import re
from decimal import Decimal, InvalidOperation

from schemas import DocumentFields, TaxLine


AMOUNT_PATTERN = re.compile(
    r"(?<![\w.])(?:[$₹€£]\s*)?[-+]?\d[\d,]*(?:\.\d{1,2})?(?!\d)"
)
MONEY_TOKEN_PATTERN = re.compile(r"(?:[$₹€£]\s*|Rs\.?\s*)[-+]?\d[\d,]*(?:\.\d{1,2})?")
TAX_PATTERN = re.compile(
    r"\b(CGST|SGST|IGST|UTGST|GST|VAT|Sales\s+Tax|Tax|Cess)\b"
    r"[^%\r\n]{0,40}?(\d+(?:\.\d+)?)\s*%",
    re.IGNORECASE,
)
TABLE_TAX_PATTERN = re.compile(
    r"(?P<rate>\d+(?:\.\d+)?)\s*%\s*"
    r"(?P<type>CGST|SGST|IGST|UTGST|GST|VAT|Sales\s+Tax|Tax|Cess)\s*"
    r"(?P<amount>(?:[$₹€£]\s*|Rs\.?\s*)[-+]?\d[\d,]*(?:\.\d{1,2})?)",
    re.IGNORECASE,
)
ADDITIONAL_CHARGE_PATTERN = re.compile(
    r"\b(?:"
    r"(?:shipping|delivery|handling|service|convenience)\s+"
    r"(?:fee|fees|charge|charges|cost|costs)|"
    r"surcharge"
    r")\b",
    re.IGNORECASE,
)


def _money_tokens(text: str) -> list[str]:
    return [match.group(0).strip() for match in MONEY_TOKEN_PATTERN.finditer(text)]


def split_invoice_pages(text: str) -> list[tuple[int, str]]:
    markers = list(re.finditer(r"(?:^|\s)Page\s+(\d+)\s*:\s*", text, re.IGNORECASE))
    if not markers:
        return [(1, text.strip())]

    pages = []
    for index, marker in enumerate(markers):
        start = marker.end()
        end = markers[index + 1].start() if index + 1 < len(markers) else len(text)
        pages.append((int(marker.group(1)), text[start:end].strip()))
    return pages


def _line_amount(line: str) -> str:
    matches = list(AMOUNT_PATTERN.finditer(line))
    if not matches:
        matches = list(re.finditer(r"[-+]?\d[\d,]*(?:\.\d{1,2})?", line))
    return matches[-1].group(0).strip() if matches else "N/A"


def _first_labeled_amount(lines: list[str], pattern: re.Pattern[str]) -> str:
    for line in lines:
        if pattern.search(line):
            amount = _line_amount(line)
            if amount != "N/A":
                return amount
    return "N/A"


class LocalExtractionService:
    def extract_fields(self, text: str) -> DocumentFields:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        normalized_text = text.lower()

        vendor_name = "N/A"
        vendor_match = re.search(
            r"\bFor\s+(.+?)\s*:\s*Authorized\s+Signatory\b", text, re.IGNORECASE
        )
        if vendor_match:
            vendor_name = vendor_match.group(1).strip()
        for line in lines[:5] if vendor_name == "N/A" else []:
            line = re.sub(r"^\s*Page\s+\d+\s*:\s*", "", line, flags=re.IGNORECASE)
            candidate = re.sub(r"\binvoice\b", "", line, flags=re.IGNORECASE)
            candidate = re.sub(r"\s+", " ", candidate).strip(" :-")
            if candidate and not re.search(r"\b(date|invoice\s*(?:no|number|#))\b", candidate, re.I):
                vendor_name = candidate
                break

        invoice_number = "N/A"
        for line in lines:
            label_match = re.search(
                r"\binvoice\s*(?:number|no\.?|#)\s*[:#]?\s*(.*)",
                line,
                re.IGNORECASE,
            )
            if label_match:
                invoice_text = label_match.group(1)
                match = re.search(r"\bINV[\W_]*\d+", invoice_text, re.IGNORECASE)
                if not match:
                    match = re.search(
                        r"\b(?:[A-Z0-9]{2,}[-_/]\d+|[A-Z]{2,}\d+|\d{3,})\b",
                        invoice_text,
                        re.IGNORECASE,
                    )
                if match:
                    invoice_number = re.sub(r"[^A-Z0-9/_-]", "", match.group(0), flags=re.I)
                    break

        date = "N/A"
        date_pattern = (
            r"\b(?:\d{4}[-/]\d{1,2}[-/]\d{1,2}|"
            r"\d{1,2}[-/.]\d{1,2}[-/.](?:\d{2}|\d{4})|"
            r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|"
            r"Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|"
            r"Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2},?\s+\d{4})\b"
        )
        date_match = re.search(
            rf"\bInvoice\s+Date\s*:\s*({date_pattern})",
            text,
            re.IGNORECASE,
        )
        if not date_match:
            date_match = re.search(date_pattern, text, re.IGNORECASE)
        if date_match:
            date = date_match.group(1) if date_match.lastindex else date_match.group(0)

        category = "N/A"
        category_patterns = (
            ("Meals/Entertainment", r"\b(restaurant|cafe|meal|dining|food)\b"),
            ("Office Supplies", r"\b(office supplies|stationery|printer|paper)\b"),
            ("Travel", r"\b(flight|airline|hotel|travel|taxi|uber)\b"),
            ("Software/SaaS", r"\b(software|subscription|cloud hosting|saas)\b"),
            ("Utilities", r"\b(electricity|utility|water bill|internet bill)\b"),
            ("Marketing", r"\b(marketing|advertising|campaign)\b"),
        )
        for value, pattern in category_patterns:
            if re.search(pattern, normalized_text):
                category = value
                break
        if category == "N/A":
            category = "Miscellaneous"

        taxable_amount = _first_labeled_amount(
            lines,
            re.compile(
                r"\b(sub[\s-]*total|taxable\s+(?:value|amount)|net\s+amount)\b",
                re.IGNORECASE,
            ),
        )
        table_header = re.search(r"\bTax\s+Amount\s+Total\s+Amount\b", text, re.I)
        if table_header:
            table_body = text[table_header.end():]
            row_end = re.search(r"\bTOTAL\s*:", table_body, re.IGNORECASE)
            if row_end:
                table_body = table_body[:row_end.start()]
            first_tax = TABLE_TAX_PATTERN.search(table_body)
            if first_tax:
                row_amounts = _money_tokens(table_body[:first_tax.start()])
                if row_amounts:
                    taxable_amount = row_amounts[-1]
        discount_amount = _first_labeled_amount(
            lines, re.compile(r"\b(discount|coupon|promo)\b", re.IGNORECASE)
        )
        if discount_amount == "N/A":
            discount_amount = "0"

        additional_charges = Decimal("0")
        for line in lines:
            charge_match = ADDITIONAL_CHARGE_PATTERN.search(line)
            if charge_match:
                amount_match = MONEY_TOKEN_PATTERN.search(line, charge_match.end())
                if amount_match is None:
                    amount_match = re.search(
                        r"(?<![\w.])[-+]?\d[\d,]*(?:\.\d{1,2})?",
                        line[charge_match.end():],
                    )
                if amount_match is None:
                    additional_charges = None
                    break
                try:
                    additional_charges += Decimal(
                        re.sub(r"[^\d.+-]", "", amount_match.group(0))
                    )
                except InvalidOperation:
                    additional_charges = None
                    break
        additional_charges_value = (
            f"{additional_charges:.2f}" if additional_charges is not None else "N/A"
        )

        taxes = []
        table_tax_matches = list(TABLE_TAX_PATTERN.finditer(text))
        for tax_match in table_tax_matches:
            tax_label = re.sub(r"\s+", " ", tax_match.group("type")).strip()
            if tax_label.upper() in {"CGST", "SGST", "IGST", "UTGST", "GST", "VAT"}:
                tax_label = tax_label.upper()
            else:
                tax_label = tax_label.title()
            taxes.append(
                TaxLine(
                    tax_type=tax_label,
                    rate=f"{tax_match.group('rate')}%",
                    amount=tax_match.group("amount").strip(),
                )
            )
        if not taxes:
            for line in lines:
                tax_match = TAX_PATTERN.search(line)
                if not tax_match:
                    continue
                amount = _line_amount(line[tax_match.end():])
                if amount == "N/A":
                    amount = _line_amount(line)
                tax_label = re.sub(r"\s+", " ", tax_match.group(1)).strip()
                if tax_label.upper() in {"CGST", "SGST", "IGST", "UTGST", "GST", "VAT"}:
                    tax_label = tax_label.upper()
                else:
                    tax_label = tax_label.title()
                taxes.append(
                    TaxLine(
                        tax_type=tax_label,
                        rate=f"{tax_match.group(2)}%",
                        amount=amount,
                    )
                )

        total_amount = "N/A"
        total_match = re.search(
            r"\bTOTAL\s*:\s*(.*?)(?=\b(?:Amount\s+in\s+Words|Invoice\s+Value|"
            r"Mode\s+of\s+Payment|Whether\s+tax)\b|$)",
            text,
            re.IGNORECASE | re.DOTALL,
        )
        if total_match:
            total_values = _money_tokens(total_match.group(1))
            if total_values:
                total_amount = total_values[-1]
        if total_amount == "N/A":
            total_amount = _first_labeled_amount(
                lines,
                re.compile(
                    r"\b(grand\s+total|invoice\s+total|total\s+amount|amount\s+payable|"
                    r"amount\s+due|balance\s+due|total\s+due)\b",
                    re.I,
                ),
            )
        if total_amount == "N/A":
            invoice_value = re.search(r"\bInvoice\s+Value\s*:\s*(.*)", text, re.I)
            if invoice_value:
                total_amount = _line_amount(invoice_value.group(1))
        if total_amount == "N/A":
            total_amount = _first_labeled_amount(
                lines, re.compile(r"\btotal\b", re.IGNORECASE)
            )
        tax_inclusive = "unknown"
        if re.search(r"\b(tax included|inclusive of tax|including tax)\b", normalized_text):
            tax_inclusive = "yes"
        elif taxes or re.search(r"\b(tax extra|plus tax|excluding tax)\b", normalized_text):
            tax_inclusive = "no"

        return DocumentFields(
            vendor_name=vendor_name,
            invoice_number=invoice_number,
            date=date,
            total_amount=total_amount,
            expense_category=category,
            taxable_amount=taxable_amount,
            discount_amount=discount_amount,
            additional_charges=additional_charges_value,
            tax_inclusive=tax_inclusive,
            taxes=taxes,
        )


local_extraction_service = LocalExtractionService()
