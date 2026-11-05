# Offline dashboard in a container. Build and run: see docs/HOSTING.md
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8050
# Listen on all container interfaces and do not try to open a browser; publish the port to 127.0.0.1 only (docs/HOSTING.md).
RUN sed -i 's/"HOST": "127.0.0.1"/"HOST": "0.0.0.0"/; s/"OPEN_BROWSER": True/"OPEN_BROWSER": False/' dashboard_dash.py
CMD ["python", "dashboard_dash.py"]
