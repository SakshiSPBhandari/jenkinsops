FROM python:3.10-slim

WORKDIR /app

COPY requirement.txt .
RUN pip install --no-cache-dir -r requirement.txt

COPY . .

EXPOSE 7860

# Default: run FastAPI server (inference.py uses HF_TOKEN env var)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]