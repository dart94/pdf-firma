from PIL import Image, ImageDraw
from PyPDF2 import PdfReader, PdfWriter
import os
from io import BytesIO

def create_signature_image(signature_data):
    # Crear una imagen de firma a partir de datos en base64 (simulación)
    img = Image.new("RGB", (400, 100), "white")
    draw = ImageDraw.Draw(img)
    draw.text((10, 10), signature_data, fill="black")
    output = BytesIO()
    img.save(output, format="PNG")
    output.seek(0)
    return output

def add_signature_to_pdf(pdf_filename, signature_image):
    # Simulación de agregar una firma a un PDF (implementación simple)
    reader = PdfReader(os.path.join('uploads', pdf_filename))
    writer = PdfWriter()

    for page in reader.pages:
        writer.add_page(page)

    output = BytesIO()
    writer.write(output)
    output.seek(0)
    return output.getvalue()
