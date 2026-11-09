modules = [
    "fastapi","pydantic","httpx","cv2","fitz","pytesseract","requests","tenacity","uvicorn"
]

import importlib
for m in modules:
    try:
        importlib.import_module(m)
        print(m, "OK")
    except Exception as e:
        print(m, "ERROR:", type(e).__name__, e)
