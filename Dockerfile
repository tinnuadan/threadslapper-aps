ARG PYTHON_VERSION=3.10-slim

FROM python:${PYTHON_VERSION}

ARG debian_frontend=noninteractive

ENV PYTHONPATH=/opt/threadslapper/src:$PYTHONPATH \
    THREADSLAPPER_LOG_PATH=/var/log

COPY Pipfile* .

RUN pip install pipenv && \
    pipenv requirements > requirements.txt && \
    pip install -r requirements.txt

WORKDIR /opt/threadslapper

COPY src .

ENTRYPOINT ["python", "-m", "threadslapper"]
