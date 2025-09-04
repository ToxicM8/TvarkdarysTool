FROM python:3.12-slim

# darbo katalogas konteineryje
WORKDIR /app

# įkeliame priklausomybes
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# įkeliame visą projektą
COPY . .

# Cloud Run naudoja PORT kintamąjį (default 8080)
ENV PORT=8080

# paleidžiam bot_core.py
CMD ["python", "bot_core.py"]
