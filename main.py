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

# Inicialización de la aplicación
app = Flask(__name__)

# Configuración
UPLOAD_FOLDER = "uploads"
SIGNED_FOLDER = "signed"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(SIGNED_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["SIGNED_FOLDER"] = SIGNED_FOLDER
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/db")
app.config["SECRET_KEY"] = os.urandom(24)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
port = int(os.environ.get('PORT', 5000))

# Inicialización de extensiones
db = SQLAlchemy(app)
migrate = Migrate(app, db)
bcrypt = Bcrypt(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Modelo de la tabla de usuarios
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

# Modelo de la tabla de firmas
class SignatureRequest(db.Model):
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

@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    if "file" not in request.files:
        return "No se subió ningún archivo", 400
    
    file = request.files["file"]
    if file.filename == "":
        return "No se seleccionó ningún archivo", 400
    
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
    signature_request = SignatureRequest.query.get_or_404(request_id)

    if signature_request.is_signed:
        return render_template('signed.html')
    if signature_request.is_expired():
        return render_template('expired.html')
    
    if request.method == 'POST':
        signature_data = request.form["signature"]
        pdf_path = os.path.join(app.config["UPLOAD_FOLDER"], signature_request.filename)
        
        try:
            signature_image = create_signature_image(signature_data)
            signed_pdf_binary = add_signature_to_pdf(pdf_path, signature_image)
        except ValueError as e:
            return str(e), 400

        signature_request.is_signed = True
        signature_request.signed_pdf = signed_pdf_binary
        db.session.commit()
        
        return render_template('signed.html')

    return render_template("sign.html", filename=signature_request.filename)

# Inicialización de la base de datos
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=port)