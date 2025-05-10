FROM python:3.10-slim
WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

# ← use sh -c so $PORT is substituted at runtime
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port $PORT"]
