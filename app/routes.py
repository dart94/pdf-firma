from flask import Blueprint, render_template, request, url_for, send_file
from app import db
from app.models import SignatureRequest
from app.utils import create_signature_image, add_signature_to_pdf
import os
import uuid
from datetime import datetime, timedelta

main_blueprint = Blueprint('main', __name__)

@main_blueprint.route('/')
def index():
    return render_template('index.html')

@main_blueprint.route('/upload', methods=['POST'])
def upload_file():
    if "file" not in request.files:
        return "No se subió ningún archivo"
    
    file = request.files["file"]
    if file.filename == "":
        return "No se seleccionó ningún archivo"
    
    filename = file.filename
    filepath = os.path.join("uploads", filename)
    file.save(filepath)
    
    request_id = str(uuid.uuid4())
    signature_request = SignatureRequest(
        id=request_id,
        filename=filename,
        expires_at=datetime.utcnow() + timedelta(days=7)
    )
    
    db.session.add(signature_request)
    db.session.commit()
    
    signing_url = url_for('main.sign_document', request_id=request_id, _external=True)
    return render_template('upload_success.html', signing_url=signing_url)

@main_blueprint.route('/sign/<request_id>', methods=['GET', 'POST'])
def sign_document(request_id):
    signature_request = SignatureRequest.query.get_or_404(request_id)
    
    if request.method == 'POST':
        signature_data = request.form["signature"]
        pdf_path = os.path.join("uploads", signature_request.filename)
        signature_image = create_signature_image(signature_data)
        signed_pdf_binary = add_signature_to_pdf(pdf_path, signature_image)
        signature_request.is_signed = True
        signature_request.signed_pdf = signed_pdf_binary
        db.session.commit()
        return "El documento fue firmado correctamente."
    
    return render_template("sign.html", filename=signature_request.filename)
