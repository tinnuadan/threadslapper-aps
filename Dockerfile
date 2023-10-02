ARG PYTHON_VERSION=3.10-slim

FROM python:${PYTHON_VERSION}

LABEL traekfik.enable=false
ARG debian_frontend=noninteractive

ENV PYTHONPATH=/opt/threadslapper/src:$PYTHONPATH \
    THREADSLAPPER_LOG_PATH=/var/log/threadslapper \
    THREADSLAPPER_CONFIG_PATH=/opt/threadslapper/config

COPY Pipfile* .

RUN pip install pipenv && \
    pipenv requirements > requirements.txt && \
    pip install -r requirements.txt && \
    mkdir -p -m 666 ${THREADSLAPPER_LOG_PATH}

WORKDIR /opt/threadslapper

COPY config .
COPY src .

ENTRYPOINT ["python", "-m", "threadslapper"]
