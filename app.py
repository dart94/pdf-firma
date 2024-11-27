import os
import uuid
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, abort
from werkzeug.utils import secure_filename
from PIL import Image
from io import BytesIO
import tempfile
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from base64 import b64decode
import pypdf
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# Configuración
UPLOAD_FOLDER = "uploads"
SIGNED_FOLDER = "signed"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(SIGNED_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["SIGNED_FOLDER"] = SIGNED_FOLDER
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///signatures.db"
app.config["SECRET_KEY"] = os.urandom(24)
port = int(os.environ.get('PORT', 5000))

db = SQLAlchemy(app)

class SignatureRequest(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    is_signed = db.Column(db.Boolean, default=False)
    
    def is_expired(self):
        return datetime.utcnow() > self.expires_at

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
    c.drawImage(temp_signature_path, 200, 350, width=140, height=40)  # Ajusta posición/tamaño
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

    # Limpiar el archivo temporal de la firma
    try:
        os.unlink(temp_signature_path)
    except:
        pass

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
    
    # Crear una nueva solicitud de firma
    request_id = str(uuid.uuid4())
    signature_request = SignatureRequest(
        id=request_id,
        filename=filename,
        expires_at=datetime.utcnow() + timedelta(days=7)  # El enlace expira en 7 días
    )
    
    db.session.add(signature_request)
    db.session.commit()
    
    # Generar URL para compartir
    signing_url = url_for('sign_document', request_id=request_id, _external=True)
    return render_template('upload_success.html', signing_url=signing_url)

@app.route('/sign/<request_id>', methods=['GET', 'POST'])
def sign_document(request_id):
    # Buscar la solicitud de firma
    signature_request = SignatureRequest.query.get_or_404(request_id)
    
    # Verificar si ya está firmado o expirado
    if signature_request.is_signed:
        return render_template('signed.html')
    if signature_request.is_expired():
        return render_template('expired.html')
    
    if request.method == 'POST':
        signature_data = request.form["signature"]
        pdf_path = os.path.join(app.config["UPLOAD_FOLDER"], signature_request.filename)
        
        # Crear imagen de la firma
        signature_image = create_signature_image(signature_data)
        
        # Insertar la firma en el PDF
        signed_filename = f"signed_{signature_request.filename}"
        signed_pdf_path = os.path.join(app.config["SIGNED_FOLDER"], signed_filename)
        add_signature_to_pdf(pdf_path, signature_image, signed_pdf_path)
        
        # Marcar como firmado
        signature_request.is_signed = True
        db.session.commit()
        
        return send_from_directory(app.config["SIGNED_FOLDER"], signed_filename, as_attachment=True)
    
    return render_template("sign.html", filename=signature_request.filename)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

@app.route('/status/<request_id>')
def signature_status(request_id):
    signature_request = SignatureRequest.query.get_or_404(request_id)
    return {
        'is_signed': signature_request.is_signed,
        'is_expired': signature_request.is_expired(),
        'expires_at': signature_request.expires_at.isoformat()
    }

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=port)