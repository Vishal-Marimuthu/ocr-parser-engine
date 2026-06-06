import os
import io
import re
import cv2
import numpy as np
import pytesseract
import fitz
from fastapi import FastAPI, File, UploadFile, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Resilient Tesseract Configuration
tesseract_paths = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    r"C:\Users\Vishal Marimuthu\AppData\Local\Programs\Tesseract-OCR\tesseract.exe",
]
for path in tesseract_paths:
    if os.path.exists(path):
        pytesseract.pytesseract.tesseract_cmd = path
        break

app = FastAPI(title="Intelligent Document OCR Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def parse_document_data(text: str) -> dict:
    invoice_patterns = [
        re.compile(r'(?:invoice\s*(?:no|number|#)?|inv\s*#?)\s*[:.-]?\s*([A-Z0-9-]+)', re.IGNORECASE),
        re.compile(r'#\s*([A-Z0-9-]+)', re.IGNORECASE)
    ]
    date_patterns = [
        re.compile(r'(?:date)\s*[:.-]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2}|[A-Za-z]+ \d{1,2},? \d{4})', re.IGNORECASE)
    ]
    amount_patterns = [
        re.compile(r'(?:total\s*(?:amount|due)?|amount\s*due|balance\s*due)\s*[:.-]?\s*(?:\$|usd|eur|£)?\s*([0-9,]+\.\d{2})', re.IGNORECASE),
        re.compile(r'(?:\$|usd|eur|£)\s*([0-9,]+\.\d{2})', re.IGNORECASE)
    ]
    
    invoice_no = "N/A"
    for pattern in invoice_patterns:
        match = pattern.search(text)
        if match:
            invoice_no = match.group(1).strip()
            break
            
    doc_date = "N/A"
    for pattern in date_patterns:
        match = pattern.search(text)
        if match:
            doc_date = match.group(1).strip()
            break
            
    total_amount = "N/A"
    for pattern in amount_patterns:
        match = pattern.search(text)
        if match:
            total_amount = match.group(1).strip()
            break
            
    return {
        "invoice_number": invoice_no,
        "date": doc_date,
        "total_amount": total_amount,
        "raw_text": text.strip()
    }

@app.post("/api/extract")
async def extract_document(file: UploadFile = File(...)):
    contents = await file.read()
    
    if file.content_type == "application/pdf" or file.filename.endswith(".pdf"):
        try:
            doc = fitz.open(stream=contents, filetype="pdf")
            text = ""
            for page in doc:
                # 1. Try direct text extraction (digital PDF)
                page_text = page.get_text()
                if page_text.strip():
                    text += page_text + "\n"
                else:
                    # 2. Scanned PDF: Render page to image and run OCR
                    pix = page.get_pixmap(dpi=150)
                    img_data = pix.tobytes("png")
                    nparr = np.frombuffer(img_data, np.uint8)
                    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    
                    if img is not None:
                        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                        # Resize to improve OCR accuracy
                        gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
                        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                        page_text = pytesseract.image_to_string(thresh)
                        text += page_text + "\n"
            
            if not text.strip():
                raise HTTPException(status_code=400, detail="Could not extract any text from the PDF.")
                
        except Exception as e:
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(status_code=500, detail=f"PDF Processing Error: {str(e)}")
    else:
        # Preprocessing Pipeline for standard images
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            raise HTTPException(status_code=400, detail="Invalid image file")
            
        # 1. Grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # 2. Resize to improve OCR accuracy on smaller text
        gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        
        # 3. Otsu's Thresholding
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Tesseract OCR
        try:
            text = pytesseract.image_to_string(thresh)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"OCR Error: {str(e)}")
        
    extracted_data = parse_document_data(text)
    return extracted_data
