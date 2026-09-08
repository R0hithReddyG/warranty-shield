# Warranty Shield — production container
FROM python:3.10-slim

WORKDIR /app

# Install system deps (if any compiled packages need them later)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first for better layer caching
COPY requirements.txt requirements_root.txt ./
RUN pip install --no-cache-dir -r requirements_root.txt

# Copy application code
COPY app/ ./app/
COPY config.yaml .streamlit/ ./
COPY app/main.py ./app/main.py

# Streamlit must listen on the port provided by the platform
ENV PORT=8501
EXPOSE 8501

CMD ["sh", "-c", "streamlit run app/main.py --server.port ${PORT} --server.address 0.0.0.0"]
