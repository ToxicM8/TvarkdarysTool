# ---- Base
FROM python:3.12-slim

# ---- Workdir
WORKDIR /app

# ---- Deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---- App
COPY . .

# ---- Env
ENV PORT=8080

# ---- Run (gunicorn ieško app objekto iš main:app)
CMD ["gunicorn", "-b", "0.0.0.0:8080", "main:app"]