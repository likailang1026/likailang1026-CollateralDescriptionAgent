# blip_model.py

import torch
from transformers import Blip2Processor, Blip2ForConditionalGeneration
from PIL import Image

device = "cuda" if torch.cuda.is_available() else "cpu"

print("Loading BLIP-2 model... This may take several minutes the first time.")

processor = Blip2Processor.from_pretrained("Salesforce/blip2-opt-2.7b")
model = Blip2ForConditionalGeneration.from_pretrained(
    "Salesforce/blip2-opt-2.7b",
    torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
    device_map="auto"  # 不要再调用 .to(device)
)

def generate_caption(image_path):
    raw_image = Image.open(image_path).convert("RGB")
    inputs = processor(raw_image, return_tensors="pt").to(device)
    output = model.generate(**inputs, max_new_tokens=50)
    return processor.decode(output[0], skip_special_tokens=True)
