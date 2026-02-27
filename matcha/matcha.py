from transformers import AutoProcessor, Pix2StructForConditionalGeneration
import requests
from PIL import Image
import torch

device = "cuda" if torch.cuda.is_available() else "cpu"

model = Pix2StructForConditionalGeneration.from_pretrained(
    "google/matcha-plotqa-v1"
).to(device)

processor = AutoProcessor.from_pretrained("google/matcha-plotqa-v1")

# url = "https://raw.githubusercontent.com/vis-nlp/ChartQA/main/ChartQA%20Dataset/val/png/20294671002019.png"
# image = Image.open(requests.get(url, stream=True).raw)
# question = "Is the sum of all 4 places greater than Laos?"

image = Image.open("image.png")
question = "what is the growth at RF power equals 300 W ? "

inputs = processor(images=image, text=question, return_tensors="pt").to(device)

predictions = model.generate(**inputs, max_new_tokens=128)

print(processor.decode(predictions[0], skip_special_tokens=True))
