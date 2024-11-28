FROM python:3.9-slim

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Copiar archivos de la aplicación
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Copiar .env al contenedor
COPY .env .env

# Comando para ejecutar migraciones y lanzar el servidor
CMD ["sh", "-c", "flask db upgrade && gunicorn app:app --bind 0.0.0.0:5000"]
