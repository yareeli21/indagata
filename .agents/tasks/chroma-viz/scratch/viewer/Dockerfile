# DEMO / THROWAWAY -- Visor read-only de vectores Chroma (FastAPI + PCA + Plotly).
# No forma parte de services/*; vive en el scratch del task.
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
