import logging

import httpx
from fastapi import APIRouter, File, HTTPException, UploadFile

from schemas import DocumentFields, ExtractionResponse, InvoiceResult
from services.local_extraction_service import (
    local_extraction_service,
    split_invoice_pages,
)
from services.llm_service import llm_service
from services.ocr_service import ocr_service
from services.tax_service import calculate_gst


logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/extract", response_model=ExtractionResponse)
async def extract_document(file: UploadFile = File(...)) -> ExtractionResponse:
    contents = await file.read()
    is_pdf = file.content_type == "application/pdf" or (
        file.filename or ""
    ).lower().endswith(".pdf")

    try:
        if is_pdf:
            ocr_result = ocr_service.process_pdf(contents)
        else:
            ocr_result = ocr_service.process_image(contents)
    except Exception as exc:
        logger.exception("OCR failed for uploaded document")
        raise HTTPException(
            status_code=422,
            detail=f"Could not read the uploaded document: {exc}",
        ) from exc

    if not ocr_result["is_valid"]:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "No readable text was found in the document.",
                "warnings": ocr_result["warnings"],
            },
        )

    page_fields = [
        (
            page_number,
            local_extraction_service.extract_fields(page_text),
        )
        for page_number, page_text in split_invoice_pages(ocr_result["clean_text"])
    ]
    local_fields = page_fields[0][1]
    extraction_warnings: list[str] = []
    try:
        ai_fields = DocumentFields.model_validate(
            await llm_service.extract_fields(ocr_result["clean_text"])
        )
        data = ai_fields.model_copy()

        if local_fields.total_amount != "N/A":
            if ai_fields.total_amount != local_fields.total_amount:
                extraction_warnings.append(
                    "The OCR-labeled invoice total differs from the AI value; the OCR value is used. Review it against the document."
                )
            data.total_amount = local_fields.total_amount
        if local_fields.taxable_amount != "N/A":
            if ai_fields.taxable_amount != local_fields.taxable_amount:
                extraction_warnings.append(
                    "The OCR-labeled taxable value differs from the AI value; the OCR value is used. Review it against the document."
                )
            data.taxable_amount = local_fields.taxable_amount
        if local_fields.taxes:
            if ai_fields.taxes != local_fields.taxes:
                extraction_warnings.append(
                    "OCR found tax lines that differ from the AI extraction; OCR tax lines are used for calculation."
                )
            data.taxes = local_fields.taxes
        if local_fields.discount_amount != "0":
            data.discount_amount = local_fields.discount_amount
        if local_fields.additional_charges not in {"0", "N/A"}:
            data.additional_charges = local_fields.additional_charges
        if local_fields.tax_inclusive != "unknown":
            data.tax_inclusive = local_fields.tax_inclusive
        extraction_method = "ai_with_ocr_checks"
    except (httpx.HTTPError, RuntimeError, ValueError, KeyError, IndexError, TypeError) as exc:
        logger.exception("AI extraction failed; using local OCR extraction")
        data = local_fields
        extraction_method = "ocr_fallback"
        extraction_warnings.append(
            "OpenRouter extraction was unavailable; local OCR rules were used. "
            "Review the extracted values against the document."
        )

    gst_check = calculate_gst(data)
    invoice_fields = [(page_fields[0][0], data)] if len(page_fields) == 1 else page_fields
    invoices = [
        InvoiceResult(
            page_number=page_number,
            data=fields,
            gst_check=calculate_gst(fields),
        )
        for page_number, fields in invoice_fields
    ]

    return ExtractionResponse(
        extracted_text=ocr_result["raw_text"],
        data=data,
        gst_check=gst_check,
        invoices=invoices,
        extraction_method=extraction_method,
        extraction_warnings=extraction_warnings,
    )
