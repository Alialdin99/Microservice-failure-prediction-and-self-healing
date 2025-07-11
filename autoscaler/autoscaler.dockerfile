FROM python:3.9-slim
WORKDIR /app

COPY autoscaler/requirements-controller.txt .
RUN pip install --no-cache-dir -r requirements-controller.txt

COPY autoscaler/ .
COPY utils ./utils

# This is a script, not a server, so we run it directly with python
CMD ["python", "autoscaler.py"]