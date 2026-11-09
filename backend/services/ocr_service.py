import os
import cv2
import numpy as np
import pytesseract
import fitz

class OCRService:
    def __init__(self):
        # Configure Tesseract paths robustly
        tesseract_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            r"C:\Users\Vishal Marimuthu\AppData\Local\Programs\Tesseract-OCR\tesseract.exe",
        ]
        for path in tesseract_paths:
            if os.path.exists(path):
                pytesseract.pytesseract.tesseract_cmd = path
                break

    def preprocess_image(self, img: np.ndarray) -> np.ndarray:
        """Apply deterministic preprocessing to improve OCR."""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Don't upscale if the image is already large enough
        h, w = gray.shape
        if max(h, w) < 2000:
            gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

        # Adaptive thresholding or Otsu's
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return thresh

    def is_valid_ocr_text(self, text: str) -> tuple[bool, list[str]]:
        """OCR Quality Gate."""
        warnings = []
        if not text or not text.strip():
            warnings.append("OCR text is completely empty.")
            return False, warnings

        alnum_count = sum(c.isalnum() for c in text)
        if alnum_count < 15:
            warnings.append(f"OCR text contains too few alphanumeric characters ({alnum_count}). It might be an abstract image or a failed OCR read.")
            return False, warnings

        return True, warnings

    def process_pdf(self, contents: bytes) -> dict:
        """Extract text from PDF (digital + OCR fallback) and paginate."""
        doc = fitz.open(stream=contents, filetype="pdf")
        page_texts = []
        warnings = []
        page_count = len(doc)

        for i, page in enumerate(doc):
            page_text = page.get_text()

            # If very little text, run OCR
            if len(page_text.strip()) < 100:
                pix = page.get_pixmap(dpi=150)
                img_data = pix.tobytes("png")
                nparr = np.frombuffer(img_data, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                if img is not None:
                    thresh = self.preprocess_image(img)
                    page_text = pytesseract.image_to_string(thresh)

            page_texts.append(page_text.strip())

        if page_count == 1:
            full_text = page_texts[0]
        else:
            full_text = "\n\n".join(
                f"Page {page_number}:\n{text}"
                for page_number, text in enumerate(page_texts, start=1)
            )

        clean_text = full_text.strip()
        is_valid, val_warnings = self.is_valid_ocr_text(clean_text)
        warnings.extend(val_warnings)

        return {
            "raw_text": full_text,
            "clean_text": clean_text,
            "page_count": page_count,
            "is_valid": is_valid,
            "warnings": warnings
        }

    def process_image(self, contents: bytes) -> dict:
        """Extract text from standard image."""
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            raise ValueError("Invalid image format.")

        thresh = self.preprocess_image(img)
        text = pytesseract.image_to_string(thresh)

        clean_text = text.strip()
        is_valid, warnings = self.is_valid_ocr_text(clean_text)

        return {
            "raw_text": text,
            "clean_text": clean_text,
            "page_count": 1,
            "is_valid": is_valid,
            "warnings": warnings
        }

ocr_service = OCRService()
