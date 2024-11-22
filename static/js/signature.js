// Canvas para la firma
const signatureCanvas = document.getElementById('signature-pad');
const signatureCtx = signatureCanvas.getContext('2d');

// Ajustar las dimensiones del canvas de la firma según el tamaño en pantalla
function resizeCanvas() {
    signatureCanvas.width = signatureCanvas.offsetWidth; // Usa el ancho calculado por CSS
    signatureCanvas.height = signatureCanvas.offsetWidth * (2 / 5); 
}

// Llamar a la función para inicializar el tamaño y al redimensionar la ventana
resizeCanvas();
window.addEventListener('resize', resizeCanvas);

// Inicializar el canvas con fondo transparente
signatureCtx.fillStyle = "rgba(255, 255, 255, 0)";
signatureCtx.fillRect(0, 0, signatureCanvas.width, signatureCanvas.height);

let drawing = false;

// Manejo de eventos para dibujar en el canvas de la firma
signatureCanvas.addEventListener('mousedown', (event) => {
    drawing = true;
    signatureCtx.beginPath(); // Reinicia el trazo
    signatureCtx.moveTo(event.offsetX, event.offsetY); // Fija el punto inicial del nuevo trazo
});

signatureCanvas.addEventListener('mouseup', () => {
    drawing = false;
    signatureCtx.beginPath(); // Reinicia el trazo después de soltar el botón
});

signatureCanvas.addEventListener('mousemove', (event) => {
    if (!drawing) return;
    signatureCtx.lineWidth = 2;
    signatureCtx.lineCap = 'round';
    signatureCtx.strokeStyle = 'black';
    signatureCtx.lineTo(event.offsetX, event.offsetY);
    signatureCtx.stroke();
});

// Función para limpiar el canvas de la firma
function clearCanvas() {
    signatureCtx.clearRect(0, 0, signatureCanvas.width, signatureCanvas.height);
    signatureCtx.fillStyle = "rgba(255, 255, 255, 0)"; // Blanco transparente
    signatureCtx.fillRect(0, 0, signatureCanvas.width, signatureCanvas.height);
}

// Función para guardar la firma
function saveSignature() {
    // Crear un nuevo canvas temporal para aplicar el fondo blanco
    const tempCanvas = document.createElement('canvas');
    const tempCtx = tempCanvas.getContext('2d');

    // Configurar el tamaño del canvas temporal igual al original
    tempCanvas.width = signatureCanvas.width;
    tempCanvas.height = signatureCanvas.height;

    // Dibujar el fondo blanco en el canvas temporal
    tempCtx.fillStyle = "#FFFFFF"; // Color blanco
    tempCtx.fillRect(0, 0, tempCanvas.width, tempCanvas.height);

    // Dibujar la firma (contenido del canvas original) sobre el fondo blanco
    tempCtx.drawImage(signatureCanvas, 0, 0);

    // Convertir el canvas temporal a una imagen base64
    const signatureData = tempCanvas.toDataURL("image/png");

    // Pasar la firma al campo oculto del formulario
    document.getElementById('signature').value = signatureData;
}

// Canvas para la previsualización del PDF
const pdfCanvas = document.getElementById('pdf-canvas');
const pdfCtx = pdfCanvas.getContext('2d');

// Recupera la URL del atributo data-url
const url = pdfCanvas.getAttribute('data-url');

// Usa PDF.js para cargar y renderizar el PDF
pdfjsLib.getDocument(url).promise.then(function(pdf) {
    pdf.getPage(1).then(function(page) {
        const viewport = page.getViewport({ scale: 1 });
        pdfCanvas.height = viewport.height;
        pdfCanvas.width = viewport.width;

        const renderContext = {
            canvasContext: pdfCtx,
            viewport: viewport
        };
        page.render(renderContext);
    });
}).catch(function(error) {
    console.error("Error al cargar el PDF:", error);
});
