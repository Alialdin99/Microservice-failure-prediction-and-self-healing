FROM python:3.9-slim
WORKDIR /app

COPY suggestion-server/requirements-suggestion.txt .
RUN pip install --no-cache-dir -r requirements-suggestion.txt

COPY suggestion-server/ .
COPY utils ./utils

EXPOSE 5000 

CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5000", "suggestion_server:app"]