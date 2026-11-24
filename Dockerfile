FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir . && order-ops --generate
EXPOSE 8000
CMD ["python", "-m", "http.server", "8000", "--directory", "site"]
