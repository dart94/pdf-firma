## CORRER EL PROGRAMA

# Requerimientos
1. Crear un archivo .env
2. Crear una base de datos local en PostgreSQL usando el archivo signatures.db dentro de instance.
3. Modificar el .env segun los datos ingresados.

# Estructura del .env (ejemplo)
``` bash
    DB_HOST=localhost
    DB_PORT=5432
    DB_NAME=signatures
    DB_USER=postgres
    DB_PASS=123
```

# Crear environment
```bash
py -3 -m venv .venv
```
```bash
.venv\Scripts\activate
```

# Instalar dependencias
```bash
pip install -r requirements.txt
```

# Agregar dependencias
```bash
pip freeze > requirements.txt
```