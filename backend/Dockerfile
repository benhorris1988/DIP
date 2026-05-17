FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

# unixODBC + MS ODBC driver dependencies are optional; install if MSSQL is needed.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl gnupg unixodbc-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
