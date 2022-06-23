
FROM tiangolo/uvicorn-gunicorn:python3.8-slim

RUN apt-get update && apt-get install -y netcat

COPY . .
RUN pip install -r req.txt

