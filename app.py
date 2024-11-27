import os
import uuid
from datetime import datetime, timedelta, timezone
from flask import Flask, render_template, request, redirect, url_for, send_file
from werkzeug.utils import secure_filename
from PIL import Image
from io import BytesIO
import tempfile
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from base64 import b64decode
import pypdf
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

app = Flask(__name__)

# Configuración
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", "postgresql://postgres:your_password@postgres.railway.internal:5432/railway"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.urandom(24)
port = int(os.environ.get("PORT", 5000))

db = SQLAlchemy(app)
migrate = Migrate(app, db)


# Modelo de la base de datos
class SignatureRequest(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now(timezone.utc))
    expires_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc) + timedelta(days=7))
    is_signed = db.Column(db.Boolean, default=False)
    signed_pdf = db.Column(db.LargeBinary, nullable=True)  # Archivo firmado en formato binario

    def is_expired(self):
        return datetime.now(timezone.utc) > self.expires_at


# Función para crear una imagen de la firma
def create_signature_image(signature_data):
    signature_bytes = b64decode(signature_data.split(",")[1])
    signature_image = Image.open(BytesIO(signature_bytes))
    signature_image = signature_image.convert("RGBA")

    # Convertir fondo blanco en transparente
    data = signature_image.getdata()
    new_data = [
        (255, 255, 255, 0) if item[:3] == (255, 255, 255) else item for item in data
    ]
    signature_image.putdata(new_data)

    # Guardar la imagen como un archivo en memoria
    image_stream = BytesIO()
    signature_image.save(image_stream, format="PNG")
    image_stream.seek(0)
    return image_stream


# Función para insertar la firma en un PDF y devolver el PDF firmado como binario
def add_signature_to_pdf(pdf_path, signature_image_stream):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_signature_file:
        temp_signature_file.write(signature_image_stream.getvalue())
        temp_signature_path = temp_signature_file.name

    # Crear el PDF con la firma
    packet = BytesIO()
    c = canvas.Canvas(packet, pagesize=letter)
    c.drawImage(temp_signature_path, 170, 150, width=150, height=30)  # Ajusta la posición/tamaño
    c.save()
    packet.seek(0)

    pdf_reader = pypdf.PdfReader(pdf_path)
    signature_pdf = pypdf.PdfReader(packet)
    pdf_writer = pypdf.PdfWriter()

    # Crear la página firmada
    combined_page = pypdf.PageObject.create_blank_page(width=letter[0], height=letter[1])
    combined_page.merge_page(pdf_reader.pages[0])
    combined_page.merge_page(signature_pdf.pages[0])
    pdf_writer.add_page(combined_page)

    # Agregar las páginas restantes
    for page in pdf_reader.pages[1:]:
        pdf_writer.add_page(page)

    # Guardar el PDF firmado en memoria
    output_stream = BytesIO()
    pdf_writer.write(output_stream)
    output_stream.seek(0)

    os.unlink(temp_signature_path)  # Limpiar archivo temporal
    return output_stream.getvalue()


# Rutas de la aplicación
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return "No se subió ningún archivo"

    file = request.files["file"]
    if file.filename == "":
        return "No se seleccionó ningún archivo"

    filename = secure_filename(file.filename)
    request_id = str(uuid.uuid4())
    signature_request = SignatureRequest(
        id=request_id,
        filename=filename,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7)
    )

    # Guardar solicitud en la base de datos
    db.session.add(signature_request)
    db.session.commit()

    # Generar URL de firma
    signing_url = url_for("sign_document", request_id=request_id, _external=True)
    return render_template("upload_success.html", signing_url=signing_url)


@app.route("/sign/<request_id>", methods=["GET", "POST"])
def sign_document(request_id):
    signature_request = SignatureRequest.query.get_or_404(request_id)

    # Verificar estado
    if signature_request.is_signed:
        return render_template("signed.html")
    if signature_request.is_expired():
        return render_template("expired.html")

    if request.method == "POST":
        signature_data = request.form["signature"]
        pdf_path = os.path.join(app.config["UPLOAD_FOLDER"], signature_request.filename)

        # Crear imagen de firma e insertar en el PDF
        signature_image = create_signature_image(signature_data)
        signed_pdf_binary = add_signature_to_pdf(pdf_path, signature_image)

        # Actualizar la base de datos con el PDF firmado
        signature_request.is_signed = True
        signature_request.signed_pdf = signed_pdf_binary
        db.session.commit()

        return "El documento fue firmado y guardado correctamente en la base de datos."

    return render_template("sign.html", filename=signature_request.filename)


@app.route("/download/<request_id>")
def download_signed_pdf(request_id):
    signature_request = SignatureRequest.query.get_or_404(request_id)

    if not signature_request.is_signed or not signature_request.signed_pdf:
        return "El documento no está firmado o no existe.", 404

    return send_file(
        BytesIO(signature_request.signed_pdf),
        download_name=f"signed_{signature_request.filename}",
        as_attachment=True,
        mimetype="application/pdf"
    )


# Crear la base de datos en el primer arranque
with app.app_context():
    db.create_all()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=port)
