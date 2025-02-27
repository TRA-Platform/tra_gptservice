FROM registry.gitlab.itorummr.com/itorum/build/docker-images/python:3.9-slim-buster
WORKDIR /app
COPY . /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev default-libmysqlclient-dev && \
    rm -rf /var/lib/apt/lists/* && \
    pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt
EXPOSE 8080

COPY init.sh /app/init.sh
COPY worker.sh /app/worker.sh

RUN chmod +x /app/init.sh
RUN chmod +x /app/worker.sh
