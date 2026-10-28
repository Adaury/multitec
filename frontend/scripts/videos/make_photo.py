"""Foto de ejemplo para el video: fachada de un colmado (dibujada, sin personas ni datos reales)."""
import os
from PIL import Image, ImageDraw, ImageFont

W, H = 1280, 860
img = Image.new("RGB", (W, H), (176, 214, 240))
d = ImageDraw.Draw(img)
d.rectangle([0, 640, W, H], fill=(120, 120, 124))  # calle
d.rectangle([0, 600, W, 640], fill=(196, 192, 184))  # acera
d.rectangle([140, 180, 1140, 600], fill=(232, 214, 168))  # edificio
d.rectangle([140, 150, 1140, 190], fill=(150, 70, 60))  # techo
d.rectangle([260, 250, 1020, 330], fill=(30, 70, 140))  # letrero
try:
    font = ImageFont.truetype("arialbd.ttf", 54)
    small = ImageFont.truetype("arial.ttf", 28)
except OSError:
    font = small = ImageFont.load_default()
d.text((640, 290), "COLMADO DON PEPE", fill=(255, 255, 255), font=font, anchor="mm")
d.rectangle([220, 380, 520, 560], fill=(120, 170, 200), outline=(60, 60, 60), width=6)  # ventana izq
d.rectangle([760, 380, 1060, 560], fill=(120, 170, 200), outline=(60, 60, 60), width=6)  # ventana der
d.rectangle([570, 360, 710, 600], fill=(110, 70, 40), outline=(50, 30, 20), width=6)  # puerta
d.ellipse([682, 480, 696, 494], fill=(230, 200, 60))
d.rectangle([60, 520, 120, 600], fill=(90, 90, 96))  # poste
d.text((640, 640), "Entrada principal", fill=(255, 255, 255), font=small, anchor="mm")
img.save(os.path.join(os.path.dirname(os.path.abspath(__file__)), "fachada.png"))
print("ok")
