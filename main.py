import os
import uuid
from datetime import datetime, timedelta, timezone
from flask import Flask, render_template, request, redirect, url_for, send_file, send_from_directory
from flask_login import LoginManager, login_user, login_required, logout_user, UserMixin
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
from flask_bcrypt import Bcrypt
from flask import flash
from dotenv import load_dotenv

# Configuración de la aplicación
app = Flask(__name__)

# Configuración de carpetas de carga
UPLOAD_FOLDER = "uploads"
SIGNED_FOLDER = "signed"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(SIGNED_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["SIGNED_FOLDER"] = SIGNED_FOLDER

load_dotenv()
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT', 3306)  # Puerto predeterminado de MySQL
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASS = os.getenv('DB_PASS')

# Configuración de la base de datos
DB_URL = f"mysql+pymysql://{DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"

# Configuración de la aplicación Flask
app.config["SQLALCHEMY_DATABASE_URI"] = DB_URL
app.config["SECRET_KEY"] = os.urandom(24)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False


# Puerto de la aplicación
port = int(os.environ.get('PORT', 5000))



# Inicialización de extensiones
db = SQLAlchemy(app)
migrate = Migrate(app, db)
bcrypt = Bcrypt(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Modelos de la base de datos
class User(db.Model, UserMixin):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class SignatureRequest(db.Model):
    __tablename__ = "signature_requests"
    id = db.Column(db.String(36), primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now(timezone.utc))
    expires_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc) + timedelta(days=7))
    is_signed = db.Column(db.Boolean, default=False)
    signed_pdf = db.Column(db.LargeBinary, nullable=True)
    
    def is_expired(self):
        return datetime.now(timezone.utc) > self.expires_at
# Función para crear la imagen de la firma
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

# Rutas de la aplicación
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            return "Credenciales inválidas", 401

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/firmados')
@login_required
def list_signed_documents():
    # Obtener todas las solicitudes que han sido firmadas
    signed_requests = SignatureRequest.query.filter_by(is_signed=True).all()

    # Renderizar una plantilla con la lista de documentos
    return render_template('firmados.html', signed_requests=signed_requests)

@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    if "file" not in request.files:
        return "No se subió ningún archivo", 400
    
    file = request.files["file"]
    if file.filename == "":
        return "No se seleccionó ningún archivo", 400
    
    
    # Validar tipo de archivo
    if not file.content_type == "application/pdf":
        return "Solo se permiten archivos PDF", 400
    
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)
    
    request_id = str(uuid.uuid4())
    signature_request = SignatureRequest(
        id=request_id,
        filename=filename,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7)
    )
    
    db.session.add(signature_request)
    db.session.commit()
    
    signing_url = url_for('sign_document', request_id=request_id, _external=True)
    return render_template('upload_success.html', signing_url=signing_url)

@app.route('/sign/<request_id>', methods=['GET', 'POST'])
def sign_document(request_id):
    # Buscar la solicitud de firma
    signature_request = SignatureRequest.query.get_or_404(request_id)

    # Verificar si la solicitud ha expirado
    if signature_request.expires_at.tzinfo is None:
        expires_at_aware = signature_request.expires_at.replace(tzinfo=timezone.utc)
    else:
        expires_at_aware = signature_request.expires_at
    
    if datetime.now(timezone.utc) > expires_at_aware:
        return render_template('expired.html')  # Si el enlace expiró, notificar
    
    # Si ya está firmado, notificar
    if signature_request.is_signed:
        return render_template('signed.html')

    if request.method == 'POST':
        signature_data = request.form["signature"]
        pdf_path = os.path.join(app.config["UPLOAD_FOLDER"], signature_request.filename)
        
        # Crear imagen de la firma
        signature_image = create_signature_image(signature_data)
        
        # Insertar la firma en el PDF y guardar el archivo en memoria
        signed_pdf_binary = add_signature_to_pdf(pdf_path, signature_image)
        
        # Actualizar la base de datos con el PDF firmado
        signature_request.is_signed = True
        signature_request.signed_pdf = signed_pdf_binary
        db.session.commit()
        
        return render_template('signed.html')

    return render_template("sign.html", filename=signature_request.filename)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        # Verificar si las contraseñas coinciden
        if password != confirm_password:
            flash("Las contraseñas no coinciden. Intenta de nuevo.", "danger")
            return render_template('register.html')

        # Verificar si el nombre de usuario ya existe
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash("El nombre de usuario ya existe. Intenta con otro.", "warning")
            return render_template('register.html')

        # Hashear la contraseña y crear el usuario
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(username=username, password=hashed_password)

        db.session.add(new_user)
        db.session.commit()

        flash("Cuenta creada exitosamente. Ahora puedes iniciar sesión.", "success")
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/download/<request_id>')
@login_required
def download_signed_pdf(request_id):
    signature_request = SignatureRequest.query.get_or_404(request_id)

    # Verificar si el PDF está firmado
    if not signature_request.is_signed or not signature_request.signed_pdf:
        return "El PDF no está firmado o no existe.", 404

    # Descargar el PDF desde la base de datos
    return send_file(
        BytesIO(signature_request.signed_pdf),
        download_name=f"signed_{signature_request.filename}",
        as_attachment=True,
        mimetype="application/pdf"
    )

#Ruta para eliminar pdf de la base de datos
@app.route('/delete/<request_id>', methods=['POST'])
@login_required
def delete_signed_pdf(request_id):
    signature_request = SignatureRequest.query.get_or_404(request_id)

    # Verificar si el PDF está firmado
    if not signature_request.is_signed or not signature_request.signed_pdf:
        return "El PDF no está firmado o no existe.", 404

    # Eliminar el PDF de la base de datos
    signature_request.signed_pdf = None
    signature_request.is_signed = False  # Si quieres también actualizar el estado
    db.session.commit()

    # Redirigir a la lista de documentos firmados
    return redirect(url_for('signed_documents'))

@app.route('/uploads/<filename>')
@login_required
def uploaded_file(filename):
    # Asegúrate de que el archivo existe y está en el directorio de uploads
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    if not os.path.isfile(filepath):
        return "Archivo no encontrado", 404
    
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

# Inicialización de la base de datos
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
