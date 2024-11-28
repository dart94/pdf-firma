FROM python:3.9-slim

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Copiar y instalar dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código fuente
COPY . .

# Ejecutar migraciones y lanzar Gunicorn
CMD ["sh", "-c", "flask db upgrade || echo 'Migraciones fallaron, continuando...' && gunicorn app:app --bind 0.0.0.0:5000"]
