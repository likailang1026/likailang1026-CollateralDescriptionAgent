# ocr_model.py

import pytesseract
from PIL import Image

# 手动指定 Tesseract 主程序路径
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def extract_text_from_image(image_path):
    image = Image.open(image_path).convert("RGB")
    text = pytesseract.image_to_string(image, lang="eng")
    return text.strip()
