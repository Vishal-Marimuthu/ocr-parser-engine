import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from schemas import DocumentFields, GSTCalculation


CENT = Decimal("0.01")
TOLERANCE = Decimal("0.02")
GST_TYPES = {"cgst", "sgst", "igst", "utgst", "gst"}


def _parse_amount(value: str) -> Decimal | None:
    normalized = value.strip()
    if not normalized or normalized.upper() in {"N/A", "NA", "NONE", "-"}:
        return None

    is_negative = normalized.startswith("(") and normalized.endswith(")")
    normalized = normalized.strip("()")
    normalized = re.sub(r"(?i)\b(?:INR|Rs\.?|Rupees)\s*", "", normalized)
    normalized = re.sub(r"[^\d,.\-+]", "", normalized).replace(",", "")
    if not re.fullmatch(r"[+-]?\d+(?:\.\d+)?", normalized):
        return None

    try:
        amount = Decimal(normalized)
    except InvalidOperation:
        return None
    return -abs(amount) if is_negative else amount


def _money(value: Decimal | None) -> str:
    if value is None:
        return "N/A"
    return f"{value.quantize(CENT, rounding=ROUND_HALF_UP):.2f}"


def _tax_rate(value: str) -> Decimal | None:
    normalized = value.strip().replace("%", "").strip()
    return _parse_amount(normalized)


def calculate_gst(fields: DocumentFields) -> GSTCalculation:
    taxable_amount = _parse_amount(fields.taxable_amount)
    declared_total = _parse_amount(fields.total_amount)
    additional_charges = _parse_amount(fields.additional_charges)
    warnings: list[str] = []
    calculated_taxes = []
    gst_total = Decimal("0")
    other_tax_total = Decimal("0")
    calculated_gst_total = Decimal("0")
    calculated_other_tax_total = Decimal("0")
    has_gst = False
    all_gst_calculated = True
    all_other_tax_calculated = True
    all_taxes_calculated = True
    any_gst_mismatch = False

    for tax in fields.taxes:
        normalized_type = re.sub(r"[^a-z]", "", tax.tax_type.lower())
        is_gst = normalized_type in GST_TYPES or normalized_type.startswith(
            ("cgst", "sgst", "igst", "utgst")
        )
        declared_tax = _parse_amount(tax.amount)
        rate = _tax_rate(tax.rate)
        calculated_tax = None
        difference = None
        status = "not_calculated"

        if declared_tax is not None:
            if is_gst:
                gst_total += declared_tax
            else:
                other_tax_total += declared_tax

        if is_gst:
            has_gst = True
        if "cess" in normalized_type:
            warnings.append(
                "Cess is included in the invoice total but is not recalculated because its basis can vary."
            )
            all_taxes_calculated = False
            if is_gst:
                all_gst_calculated = False
            else:
                all_other_tax_calculated = False
        elif taxable_amount is None or rate is None or declared_tax is None:
            all_taxes_calculated = False
            if is_gst:
                all_gst_calculated = False
            else:
                all_other_tax_calculated = False
        else:
            calculated_tax = (taxable_amount * rate / Decimal("100")).quantize(
                CENT, rounding=ROUND_HALF_UP
            )
            difference = declared_tax - calculated_tax
            status = (
                "matches"
                if difference == 0
                else "rounding_difference"
                if abs(difference) <= TOLERANCE
                else "mismatch"
            )
            if is_gst:
                calculated_gst_total += calculated_tax
                any_gst_mismatch |= status == "mismatch"
            else:
                calculated_other_tax_total += calculated_tax

        if declared_tax is None:
            warnings.append(f"The amount for {tax.tax_type} could not be read.")
        elif rate is None and "cess" not in normalized_type:
            warnings.append(f"The rate for {tax.tax_type} could not be read.")

        calculated_taxes.append(
            {
                "tax_type": tax.tax_type,
                "rate": tax.rate,
                "declared_amount": _money(declared_tax),
                "calculated_amount": _money(calculated_tax),
                "difference": _money(difference),
                "status": status,
            }
        )

    if not has_gst:
        tax_status = "no_gst"
        if fields.taxes:
            warnings.append("No recognized GST components were found in the extracted tax lines.")
    elif any_gst_mismatch:
        tax_status = "mismatch"
        warnings.append("One or more GST amounts differ from the calculated amount by more than 0.02.")
    elif all_gst_calculated:
        tax_status = (
            "rounding_difference"
            if any(tax["status"] == "rounding_difference" for tax in calculated_taxes)
            else "verified"
        )
        if tax_status == "rounding_difference":
            warnings.append(
                "One or more printed tax amounts differ from standard rounding by no more than 0.02."
            )
    else:
        tax_status = "incomplete"
        warnings.append("GST could not be fully verified because a taxable value, rate, or tax amount is missing.")

    calculated_total = None
    total_difference = None
    if fields.tax_inclusive == "yes":
        total_status = "tax_inclusive"
        warnings.append(
            "The invoice is marked tax-inclusive, so the total was not recalculated by adding GST again."
        )
    elif fields.tax_inclusive == "unknown":
        total_status = "incomplete"
        warnings.append(
            "The invoice does not clearly show whether tax is included, so the total was not recalculated."
        )
    elif (
        taxable_amount is None
        or declared_total is None
        or additional_charges is None
        or any(_parse_amount(tax.amount) is None for tax in fields.taxes)
    ):
        total_status = "incomplete"
        warnings.append(
            "The payable total could not be calculated because the taxable value, declared total, charges, or a tax amount is missing."
        )
    else:
        calculated_total = taxable_amount + additional_charges + gst_total + other_tax_total
        total_difference = declared_total - calculated_total
        total_status = (
            "matches"
            if total_difference == 0
            else "rounding_difference"
            if abs(total_difference) <= TOLERANCE
            else "mismatch"
        )
        if total_status == "mismatch":
            warnings.append(
                "The invoice total differs from the calculated total by more than 0.02. Check discounts, fees, and extracted line items."
            )

    recalculated_total = None
    recalculated_difference = None
    if fields.tax_inclusive == "yes":
        recalculated_total_status = "tax_inclusive"
    elif (
        fields.tax_inclusive == "unknown"
        or taxable_amount is None
        or declared_total is None
        or additional_charges is None
        or not all_taxes_calculated
    ):
        recalculated_total_status = "incomplete"
    else:
        recalculated_total = (
            taxable_amount + additional_charges
            + calculated_gst_total + calculated_other_tax_total
        )
        recalculated_difference = declared_total - recalculated_total
        recalculated_total_status = (
            "matches"
            if recalculated_difference == 0
            else "rounding_difference"
            if abs(recalculated_difference) <= TOLERANCE
            else "mismatch"
        )

    return GSTCalculation(
        tax_status=tax_status,
        total_status=total_status,
        declared_total=_money(declared_total),
        calculated_total=_money(calculated_total),
        total_difference=_money(total_difference),
        gst_total=_money(gst_total) if has_gst else "0.00",
        other_tax_total=_money(other_tax_total),
        calculated_gst_total=(
            _money(calculated_gst_total)
            if all_gst_calculated
            else "N/A"
        ),
        calculated_other_tax_total=(
            _money(calculated_other_tax_total)
            if all_other_tax_calculated
            else "N/A"
        ),
        recalculated_total=_money(recalculated_total),
        recalculated_difference=_money(recalculated_difference),
        recalculated_total_status=recalculated_total_status,
        taxes=calculated_taxes,
        warnings=warnings,
    )
