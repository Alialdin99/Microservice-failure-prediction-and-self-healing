# Use a slim Python base image
FROM python:3.9-slim

WORKDIR /app

COPY model-server/requirements-model.txt .
RUN pip install --no-cache-dir -r requirements-model.txt

COPY model-server/ .
COPY utils ./utils

RUN apt-get update && apt-get install -y libgl1 libglib2.0-0

EXPOSE 8000

# Run the app with Gunicorn
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:8000", "model_server:app"]