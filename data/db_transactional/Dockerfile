# Usamos una imagen oficial y ligera de Python
FROM python:3.10-slim

# Establecemos el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copiamos el archivo de requerimientos y los instalamos
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el script de inicialización y el archivo SQL
COPY init_db.py .
COPY CREAR_TABLAS.sql . 

# Comando que se ejecutará cuando el contenedor inicie
CMD ["python", "init_db.py"]