FROM python:3.9-slim

# set working directory inside the container
WORKDIR /app

# install dependencies first (better layer caching - dependencies change less often than code)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copy the actual application code
COPY app.py .

# flask runs on port 5000
EXPOSE 5000

# use gunicorn for production instead of the flask dev server
# 4 workers is a reasonable default for handling concurrent requests
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "120", "app:app"]

