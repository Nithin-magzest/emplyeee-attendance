FROM python:3.11-slim

# compose.yaml runs this image with a read-only root filesystem — without
# this, Python would try (and silently fail) to write .pyc cache files
# into /app on every import.
ENV PYTHONDONTWRITEBYTECODE=1

# System deps: OpenCV / dlib (face_recognition), SSL
# (no Postgres client dev package needed — psycopg2-binary ships precompiled)
RUN apt-get update && apt-get install -y --no-install-recommends \
    cmake g++ make \
    libboost-all-dev \
    libopenblas-dev liblapack-dev \
    libx11-dev \
    libgl1 libglib2.0-0 \
    libssl-dev \
    pkg-config \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Runtime directories that are gitignored
RUN mkdir -p static/qrcodes static/employee_docs dataset

EXPOSE 5000

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
