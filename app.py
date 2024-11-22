import os
from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from werkzeug.utils import secure_filename
from PIL import Image
from io import BytesIO
import tempfile
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from base64 import b64decode
import pypdf

app = Flask(__name__)

# Configuración
UPLOAD_FOLDER = "uploads"
SIGNED_FOLDER = "signed"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(SIGNED_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["SIGNED_FOLDER"] = SIGNED_FOLDER


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    if "file" not in request.files:
        return "No se subió ningún archivo"
    
    file = request.files["file"]
    if file.filename == "":
        return "No se seleccionó ningún archivo"
    
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)
    return redirect(url_for("sign_pdf", filename=filename))


@app.route('/sign/<filename>', methods=['GET', 'POST'])
def sign_pdf(filename):
    if request.method == 'POST':
        signature_data = request.form["signature"]
        pdf_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)

        # Crear imagen de la firma desde los datos enviados (base64)
        signature_image = create_signature_image(signature_data)

        # Insertar la firma en el PDF
        signed_pdf_path = os.path.join(app.config["SIGNED_FOLDER"], f"signed_{filename}")
        add_signature_to_pdf(pdf_path, signature_image, signed_pdf_path)

        return send_from_directory(app.config["SIGNED_FOLDER"], f"signed_{filename}", as_attachment=True)

    return render_template("sign.html", filename=filename)


def create_signature_image(signature_data):
    # Decodifica los datos base64 de la firma
    signature_bytes = b64decode(signature_data.split(",")[1])
    signature_image = Image.open(BytesIO(signature_bytes))

    # Asegurar que la imagen tenga un canal alpha (transparencia)
    signature_image = signature_image.convert("RGBA")
    data = signature_image.getdata()

    # Convertir cualquier fondo blanco en transparente
    new_data = []
    for item in data:
        # Si es blanco (255, 255, 255), hacer transparente
        if item[:3] == (255, 255, 255):
            new_data.append((255, 255, 255, 0))  # Transparente
        else:
            new_data.append(item)

    signature_image.putdata(new_data)

    # Guardar la imagen como un archivo en memoria
    image_stream = BytesIO()
    signature_image.save(image_stream, format="PNG")
    image_stream.seek(0)  # Volver al inicio del flujo
    return image_stream


def add_signature_to_pdf(pdf_path, signature_image_stream, signed_pdf_path):
    # Guardar la firma en un archivo temporal
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_signature_file:
        temp_signature_file.write(signature_image_stream.getvalue())
        temp_signature_path = temp_signature_file.name

    # Crear un archivo temporal con la firma como PDF
    packet = BytesIO()
    c = canvas.Canvas(packet, pagesize=letter)

    # Dibuja la firma en la posición deseada
    c.drawImage(temp_signature_path, 170, 150, width=150, height=30)  # Ajusta posición/tamaño
    c.save()

    # Volver al inicio del archivo en memoria
    packet.seek(0)

    # Leer el PDF original y el PDF con la firma
    pdf_reader = pypdf.PdfReader(pdf_path)
    signature_pdf = pypdf.PdfReader(packet)
    pdf_writer = pypdf.PdfWriter()

    # Crear una página combinada con la firma
    original_page = pdf_reader.pages[0]
    signature_page = signature_pdf.pages[0]

    # Crear una nueva página en blanco
    combined_page = pypdf.PageObject.create_blank_page(width=letter[0], height=letter[1])

    # Agregar contenido original
    combined_page.merge_page(original_page)

    # Agregar la firma
    combined_page.merge_page(signature_page)

    # Agregar la página combinada al escritor
    pdf_writer.add_page(combined_page)

    # Agregar las demás páginas originales (si hay)
    for page in pdf_reader.pages[1:]:
        pdf_writer.add_page(page)

    # Guardar el nuevo PDF firmado
    with open(signed_pdf_path, "wb") as output_pdf:
        pdf_writer.write(output_pdf)


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


if __name__ == '__main__':
    app.run(debug=True)
