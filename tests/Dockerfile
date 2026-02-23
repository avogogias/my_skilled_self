FROM python:3.12-slim

WORKDIR /tests

RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy agent source so we can import skills directly in unit tests
COPY ../agent /agent

COPY . .

ENV PYTHONPATH=/agent

CMD ["pytest", "-v", "--tb=short", "--cov=/agent", "--cov-report=term-missing"]
