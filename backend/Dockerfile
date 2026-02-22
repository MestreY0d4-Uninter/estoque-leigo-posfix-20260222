FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install --no-cache-dir -U pip

# Install deps
COPY backend/pyproject.toml ./pyproject.toml
RUN pip install --no-cache-dir .

# App code
COPY backend/app ./app

# Frontend static assets (served by FastAPI)
COPY frontend ./frontend

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
