import os
import uuid
from datetime import datetime, timedelta, timezone
from flask import Flask, render_template, request, redirect, url_for, send_file, send_from_directory, session
from flask_login import LoginManager, login_user, login_required, logout_user, UserMixin
from werkzeug.utils import secure_filename
from io import BytesIO
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_bcrypt import Bcrypt
from flask import flash
from dotenv import load_dotenv
from functions import create_signature_image, add_signature_to_pdf
from flask_login import current_user


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
DB_PORT = os.getenv('DB_PORT')
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASS = os.getenv('DB_PASS')

DB_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Configuración de base de datos con manejo de codificación
app.config["SQLALCHEMY_DATABASE_URI"] = DB_URL
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    'connect_args': {
        'client_encoding': 'utf8'
    }
}
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

# Modelo de la tabla de usuarios
class User(db.Model, UserMixin):
    __tablename__ = "users"  # Define explícitamente el nombre de la tabla

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="cliente")  # admin o cliente

    # Representación para depuración
    def __repr__(self):
        return f"<User {self.id}: {self.username} ({self.role})>"

# Modelo de la tabla de firmas
class SignatureRequest(db.Model):
    __tablename__ = 'signature_request'

    id = db.Column(db.String(36), primary_key=True)  # UUID como ID
    filename = db.Column(db.String(255), nullable=False)  # Nombre del archivo
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))  # Fecha de creación
    expires_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc) + timedelta(days=7))  # Fecha de expiración
    is_signed = db.Column(db.Boolean, default=False, nullable=False)  # Estado de la firma
    signed_pdf = db.Column(db.LargeBinary, nullable=True)  # PDF firmado en formato binario
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Relación con la tabla users
    signed_at = db.Column(db.DateTime, nullable=True)  # Nueva columna

    # Relación para acceso al usuario
    user = db.relationship('User', backref='signature_requests', lazy=True)

    # Método para verificar si la solicitud está expirada
    def is_expired(self):
        return datetime.now(timezone.utc) > self.expires_at

    # Representación para depuración
    def __repr__(self):
        return f"<SignatureRequest {self.id}: {self.filename} (Signed: {self.is_signed})>"

# Rutas de la aplicación
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))  # Redirige a la página principal si ya inició sesión
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Consulta la tabla "users" usando el modelo User
        user = User.query.filter_by(username=username).first()

        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            session['username'] = user.username
            session['role'] = user.role
            flash(f"Inicio de sesión exitoso como {user.role}", "success")
            return redirect(url_for('index'))
        else:
            flash("Credenciales inválidas", "danger")
            return render_template('login.html')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    flash("Has cerrado sesión correctamente", "success")
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/firmados')
@login_required
def list_signed_documents():
    # Documentos firmados por el usuario actual
    signed_requests = SignatureRequest.query.filter_by(
        is_signed=True, 
        user_id=current_user.id
    ).all()

    # Documentos no firmados por el usuario actual
    unsigned_requests = SignatureRequest.query.filter_by(
        is_signed=False, 
        user_id=current_user.id
    ).all()

    # Renderizar la plantilla con ambas listas
    return render_template(
        'firmados.html',
        signed_requests=signed_requests,
        unsigned_requests=unsigned_requests
    )
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
    
    user_id = current_user.id

    request_id = str(uuid.uuid4())
    signature_request = SignatureRequest(
        id=request_id,
        filename=filename,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        user_id=user_id
    )
    
    db.session.add(signature_request)
    db.session.commit()
    
    signing_url = url_for('sign_document', request_id=request_id, _external=True)
    return render_template('upload_success.html', signing_url=signing_url)

@app.route('/sign/<request_id>', methods=['GET', 'POST'])
def sign_document(request_id):
    signature_request = SignatureRequest.query.get_or_404(request_id)

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
        signature_request.signed_at = datetime.now()
        signature_request.signed_pdf = signed_pdf_binary
        db.session.commit()
        flash("Documento firmado correctamente.", "success")
        
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
    return redirect(url_for('firmados'))

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
