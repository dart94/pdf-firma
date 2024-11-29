from flask import Blueprint, render_template, request, redirect, url_for, send_file, flash
from .models import SignatureRequest
from . import db
from .pdf_utils import create_signature_image, add_signature_to_pdf
import os
import uuid
from datetime import datetime, timedelta
from io import BytesIO

main = Blueprint("main", __name__)

@main.route('/')
def index():
    return render_template('index.html')

@main.route('/upload', methods=['POST'])
def upload_pdf():
    if 'file' not in request.files:
        flash('No file part')
        return redirect(url_for('main.index'))

    file = request.files['file']
    if file.filename == '':
        flash('No selected file')
        return redirect(url_for('main.index'))

    if file:
        # Generar un ID único para el archivo
        file_id = str(uuid.uuid4())
        filename = f"{file_id}.pdf"
        filepath = os.path.join('uploads', filename)
        file.save(filepath)

        # Crear un registro en la base de datos
        new_request = SignatureRequest(
            id=file_id,
            filename=filename,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=7)
        )
        db.session.add(new_request)
        db.session.commit()

        return redirect(url_for('main.view_pdf', file_id=file_id))

@main.route('/view/<file_id>')
def view_pdf(file_id):
    signature_request = SignatureRequest.query.get_or_404(file_id)
    return render_template('view_pdf.html', signature_request=signature_request)

@main.route('/sign/<file_id>', methods=['POST'])
def sign_pdf(file_id):
    signature_request = SignatureRequest.query.get_or_404(file_id)
    signature_image = create_signature_image(request.form['signature_data'])

    # Agregar la firma al PDF
    signed_pdf = add_signature_to_pdf(signature_request.filename, signature_image)

    # Guardar el archivo firmado
    signature_request.is_signed = True
    signature_request.signed_pdf = signed_pdf
    db.session.commit()

    return redirect(url_for('main.download_signed_pdf', file_id=file_id))

@main.route('/download/<file_id>')
def download_signed_pdf(file_id):
    signature_request = SignatureRequest.query.get_or_404(file_id)
    if not signature_request.is_signed:
        flash("El archivo no ha sido firmado aún.")
        return redirect(url_for('main.index'))

    return send_file(
        BytesIO(signature_request.signed_pdf),
        as_attachment=True,
        download_name=f"signed_{signature_request.filename}",
        mimetype="application/pdf"
    )
