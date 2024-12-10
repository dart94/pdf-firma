import os
from base64 import b64decode
from io import BytesIO
from PIL import Image
import tempfile
from reportlab.pdfgen import canvas
import pypdf
from reportlab.lib.pagesizes import letter
from base64 import b64decode

def create_signature_image(signature_data):
    try:
        signature_bytes = b64decode(signature_data.split(",")[1])
        signature_image = Image.open(BytesIO(signature_bytes))
        signature_image = signature_image.convert("RGBA")
        data = signature_image.getdata()

        new_data = [
            (255, 255, 255, 0) if item[:3] == (255, 255, 255) else item
            for item in data
        ]
        signature_image.putdata(new_data)

        image_stream = BytesIO()
        signature_image.save(image_stream, format="PNG")
        image_stream.seek(0)
        return image_stream
    except Exception as e:
        raise ValueError("Error al procesar la imagen de la firma.") from e

# Función para agregar la firma al PDF


def add_signature_to_pdf(pdf_path, signature_image_stream):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_signature_file:
        temp_signature_file.write(signature_image_stream.getvalue())
        temp_signature_path = temp_signature_file.name

    packet = BytesIO()
    c = canvas.Canvas(packet, pagesize=letter)
    c.drawImage(temp_signature_path, 170, 150, width=150, height=30)
    c.save()
    packet.seek(0)

    pdf_reader = pypdf.PdfReader(pdf_path)
    signature_pdf = pypdf.PdfReader(packet)
    pdf_writer = pypdf.PdfWriter()

    original_page = pdf_reader.pages[0]
    signature_page = signature_pdf.pages[0]
    combined_page = pypdf.PageObject.create_blank_page(width=letter[0], height=letter[1])
    combined_page.merge_page(original_page)
    combined_page.merge_page(signature_page)
    pdf_writer.add_page(combined_page)

    for page in pdf_reader.pages[1:]:
        pdf_writer.add_page(page)

    output_stream = BytesIO()
    pdf_writer.write(output_stream)
    output_stream.seek(0)

    os.unlink(temp_signature_path)
    return output_stream.getvalue()
