// Canvas para la firma
const signatureCanvas = document.getElementById('signature-pad');
const signatureCtx = signatureCanvas.getContext('2d');

// Detecta si el dispositivo tiene soporte táctil
const isTouchDevice = 'ontouchstart' in window || navigator.maxTouchPoints > 0;

// Ajustar las dimensiones del canvas de la firma según el tamaño en pantalla
function resizeCanvas() {
    signatureCanvas.width = signatureCanvas.offsetWidth; // Usa el ancho calculado por CSS
    signatureCanvas.height = signatureCanvas.offsetWidth * (2 / 5); 
}

// Inicializar el tamaño del canvas
resizeCanvas();
window.addEventListener('resize', resizeCanvas);

// Inicializar el canvas con fondo transparente
signatureCtx.fillStyle = "rgba(255, 255, 255, 0)";
signatureCtx.fillRect(0, 0, signatureCanvas.width, signatureCanvas.height);

// Variables para el estado del dibujo
let drawing = false;

// Función para obtener las coordenadas correctas (táctil o ratón)
function getEventPosition(event) {
    if (event.touches) {
        const touch = event.touches[0];
        const rect = signatureCanvas.getBoundingClientRect();
        return {
            x: touch.clientX - rect.left,
            y: touch.clientY - rect.top
        };
    } else {
        return {
            x: event.offsetX,
            y: event.offsetY
        };
    }
}

// Eventos comunes para dibujar en el canvas
function startDrawing(event) {
    drawing = true;
    const position = getEventPosition(event);
    signatureCtx.beginPath();
    signatureCtx.moveTo(position.x, position.y);
    event.preventDefault(); // Previene el scroll en dispositivos móviles
}

function stopDrawing() {
    drawing = false;
    signatureCtx.beginPath(); // Reinicia el trazo
}

function draw(event) {
    if (!drawing) return;
    const position = getEventPosition(event);
    signatureCtx.lineWidth = 2;
    signatureCtx.lineCap = 'round';
    signatureCtx.strokeStyle = 'black';
    signatureCtx.lineTo(position.x, position.y);
    signatureCtx.stroke();
    event.preventDefault(); // Previene el scroll en dispositivos móviles
}

// Añadir eventos según el dispositivo
if (isTouchDevice) {
    signatureCanvas.addEventListener('touchstart', startDrawing);
    signatureCanvas.addEventListener('touchend', stopDrawing);
    signatureCanvas.addEventListener('touchmove', draw);
} else {
    signatureCanvas.addEventListener('mousedown', startDrawing);
    signatureCanvas.addEventListener('mouseup', stopDrawing);
    signatureCanvas.addEventListener('mousemove', draw);
}

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
if (pdfCanvas) {
    const pdfCtx = pdfCanvas.getContext('2d');
    const url = pdfCanvas.getAttribute('data-url'); // Recupera la URL del atributo data-url

    // Usa PDF.js para cargar y renderizar el PDF
    pdfjsLib.getDocument(url).promise.then(function(pdf) {
        pdf.getPage(1).then(function(page) {
            const viewport = page.getViewport({ scale: 1.5 }); // Ajustar el escalado según el tamaño deseado
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
}

function copyUrl() {
    const url = document.getElementById('signing-url').textContent;
    navigator.clipboard.writeText(url).then(() => {
        alert('¡Enlace copiado al portapapeles!');
    });
}
