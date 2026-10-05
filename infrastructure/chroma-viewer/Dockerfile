# Visor read-only de vectores Chroma (FastAPI + PCA + Plotly).
# Herramienta de diagnóstico/inspección: NO es un microservicio del dominio.
# Lee ChromaDB por HTTP (API v2) y pinta un dispersograma 2D (PCA) de los
# embeddings por colección. No escribe en Chroma.
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
