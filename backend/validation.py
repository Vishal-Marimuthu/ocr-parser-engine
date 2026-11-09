import re
from typing import List
from schemas import CreatorExtractionSchema

ALLOWED_CATEGORIES = {
    "Meals/Entertainment",
    "Office Supplies",
    "Travel",
    "Software/SaaS",
    "Utilities",
    "Marketing",
    "Miscellaneous"
}

from schemas import CreatorExtractionSchema, ReviewerExtractionSchema
from typing import Union, List

def validate_extraction(extraction: Union[CreatorExtractionSchema, ReviewerExtractionSchema]) -> List[str]:
    """Step 4: Deterministic validation on the final JSON."""
    warnings = []

    # Validate Invoice Number
    invoice_val = extraction.invoice_number.value
    if invoice_val and invoice_val != "N/A":
        # Reject obvious phone numbers
        if re.match(r'^[\+]?[(]?[0-9]{3}[)]?[-\s\.]?[0-9]{3}[-\s\.]?[0-9]{4,6}$', invoice_val):
            warnings.append(f"Invoice number '{invoice_val}' looks like a phone number.")
        # Reject pure GSTIN like identifiers if labeled incorrectly (very basic check)
        if len(invoice_val) == 15 and re.match(r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$', invoice_val):
            warnings.append(f"Invoice number '{invoice_val}' looks like a GSTIN.")
        # Reject PAN numbers
        if len(invoice_val) == 10 and re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$', invoice_val):
            warnings.append(f"Invoice number '{invoice_val}' looks like a PAN number.")

    # Validate Date
    date_val = extraction.date.value
    if date_val and date_val != "N/A":
        # Basic check for impossible years
        year_match = re.search(r'(19|20)\d{2}', date_val)
        if year_match:
            year = int(year_match.group())
            if year > 2030 or year < 1990:
                warnings.append(f"Date '{date_val}' contains an unlikely year ({year}).")

    # Validate Total Amount
    amount_val = extraction.total_amount.value
    if amount_val and amount_val != "N/A":
        # Remove commas, spaces, currency symbols to check if it's numeric
        clean_amount = re.sub(r'[^\d\.]', '', amount_val)
        if not clean_amount:
            warnings.append(f"Total amount '{amount_val}' does not appear to contain numbers.")
        elif clean_amount.count('.') > 1:
            warnings.append(f"Total amount '{amount_val}' contains multiple decimal points.")

    # Validate Expense Category
    cat_val = extraction.expense_category.value
    if cat_val not in ALLOWED_CATEGORIES and cat_val != "N/A":
        warnings.append(f"Expense category '{cat_val}' is not in the allowed list.")

    # Validate Vendor Name
    vendor_val = extraction.vendor_name.value
    if vendor_val and vendor_val != "N/A":
        if len(vendor_val) > 100:
             warnings.append(f"Vendor name is unusually long ({len(vendor_val)} chars). May be an address block.")
        elif re.search(r'\b(street|st|ave|avenue|blvd|boulevard|road|rd|suite|ste|floor|fl)\b', vendor_val, re.IGNORECASE):
             warnings.append(f"Vendor name '{vendor_val}' contains address-like keywords. Please verify it's the actual vendor name.")

    return warnings
