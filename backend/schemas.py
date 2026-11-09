from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TaxLine(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tax_type: str
    rate: str
    amount: str


class DocumentFields(BaseModel):
    model_config = ConfigDict(extra="forbid")

    vendor_name: str
    invoice_number: str
    date: str
    total_amount: str
    expense_category: str
    taxable_amount: str
    discount_amount: str
    additional_charges: str
    tax_inclusive: Literal["yes", "no", "unknown"]
    taxes: list[TaxLine]


class CalculatedTaxLine(BaseModel):
    tax_type: str
    rate: str
    declared_amount: str
    calculated_amount: str
    difference: str
    status: Literal["matches", "rounding_difference", "mismatch", "not_calculated"]


class GSTCalculation(BaseModel):
    tax_status: Literal[
        "verified", "rounding_difference", "mismatch", "incomplete", "no_gst"
    ]
    total_status: Literal[
        "matches", "rounding_difference", "mismatch", "incomplete", "tax_inclusive"
    ]
    declared_total: str
    calculated_total: str
    total_difference: str
    gst_total: str
    other_tax_total: str
    calculated_gst_total: str
    calculated_other_tax_total: str
    recalculated_total: str
    recalculated_difference: str
    recalculated_total_status: Literal[
        "matches", "rounding_difference", "mismatch", "incomplete", "tax_inclusive"
    ]
    taxes: list[CalculatedTaxLine]
    warnings: list[str]


class InvoiceResult(BaseModel):
    page_number: int
    data: DocumentFields
    gst_check: GSTCalculation


class ExtractionResponse(BaseModel):
    extracted_text: str
    data: DocumentFields
    gst_check: GSTCalculation
    invoices: list[InvoiceResult] = Field(default_factory=list)
    extraction_method: Literal["ai_with_ocr_checks", "ocr_fallback"]
    extraction_warnings: list[str]
