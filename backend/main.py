import os
import io
import re
import cv2
import json
import numpy as np
import pytesseract
import fitz
import requests
import toons
from dotenv import load_dotenv
from fastapi import FastAPI, File, UploadFile, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Load environment variables from .env file
load_dotenv()

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

def parse_document_data_llm(text: str) -> dict:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("Warning: OPENROUTER_API_KEY is not set.")
        return {
            "invoice_number": "N/A",
            "date": "N/A",
            "total_amount": "N/A",
            "vendor_name": "N/A",
            "expense_category": "N/A"
        }
        
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://opticforge.netlify.app",
        "X-Title": "OpticForge OCR Engine"
    }
    
    prompt = f"""You are an expert document parser. Parse the following OCR text extracted from an invoice or receipt.
Extract the following fields and return them in a strict JSON format:
- invoice_number (string, default "N/A" if not found)
- date (string, default "N/A" if not found)
- total_amount (string, default "N/A" if not found)
- vendor_name (string, default "N/A" if not found)
- expense_category (string, default "N/A" if not found. Classify into one of these categories: Meals/Entertainment, Office Supplies, Travel, Software/SaaS, Utilities, Marketing, Miscellaneous)

Do not include any markdown formatting (like ```json ... ```) or extra explanation. Return ONLY the raw JSON string.

OCR Text:
{text}
"""
    
    payload = {
        "model": "meta-llama/llama-3-8b-instruct:free",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "response_format": {"type": "json_object"}
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=20)
        response.raise_for_status()
        res_data = response.json()
        content = res_data["choices"][0]["message"]["content"]
        
        # Clean potential markdown wrapping
        content = content.strip()
        if content.startswith("```"):
            content = re.sub(r"^```(?:json)?", "", content, flags=re.IGNORECASE).strip()
            content = re.sub(r"```$", "", content).strip()
            
        parsed = json.loads(content)
        return {
            "invoice_number": parsed.get("invoice_number", "N/A"),
            "date": parsed.get("date", "N/A"),
            "total_amount": parsed.get("total_amount", "N/A"),
            "vendor_name": parsed.get("vendor_name", "N/A"),
            "expense_category": parsed.get("expense_category", "N/A")
        }
    except Exception as e:
        print(f"Error parsing document with LLM: {e}")
        return {
            "invoice_number": "N/A",
            "date": "N/A",
            "total_amount": "N/A",
            "vendor_name": "N/A",
            "expense_category": "N/A"
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
        
    extracted_data = parse_document_data_llm(text)
    extracted_data["raw_text"] = text.strip()
    
    # Serialize to TOON format
    toon_data = toons.dumps(extracted_data)
    
    return Response(content=toon_data, media_type="text/toon")

