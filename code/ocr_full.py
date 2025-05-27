# ocr_full.py

import os
import cv2
import numpy as np
from paddleocr import PaddleOCR

# 初始化OCR，使用更轻量级的模型
ocr = PaddleOCR(use_angle_cls=False, 
                lang='en',
                use_gpu=False,
                show_log=False)

def extract_ocr_text(image_path: str) -> str:
    """Extract text from image using PaddleOCR."""
    try:
        # 读取图像
        img = cv2.imread(image_path)
        if img is None:
            return "[Error: Could not read image]"
            
        # OCR处理
        result = ocr.ocr(img, cls=False)
        if not result or not result[0]:
            return "[No text detected]"
            
        # 提取文本
        texts = []
        for line in result[0]:
            if line[1][0]:  # 文本内容
                texts.append(line[1][0])
                
        return "\n".join(texts)
        
    except Exception as e:
        return f"[OCR Error: {str(e)}]"
