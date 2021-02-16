# Dockerfile for Cray Boot Orchestration Service (BOS)
# Copyright 2019-2021 Hewlett Packard Enterprise Development LP

# Generate API
FROM openapitools/openapi-generator-cli:v4.1.2 as codegen
WORKDIR /app
COPY api/openapi.yaml api/openapi.yaml
COPY config/autogen-server.json config/autogen-server.json
COPY src/server/.openapi-generator-ignore lib/server/.openapi-generator-ignore
RUN /usr/local/bin/docker-entrypoint.sh generate \
    -i api/openapi.yaml \
    -g python-flask \
    -o lib/server \
    -c config/autogen-server.json \
    --generate-alias-as-model

# Base image
FROM dtr.dev.cray.com/baseos/alpine:3.12.0 as base
WORKDIR /app
COPY --from=codegen /app .
COPY constraints.txt requirements.txt ./
RUN apk add --no-cache gcc g++ python3-dev py3-pip musl-dev libffi-dev openssl-dev && \
    pip3 install --no-cache-dir -U pip && \
    pip3 install --no-cache-dir -r requirements.txt
COPY src/server/bos/controllers lib/server/bos/controllers
COPY src/server/bos/__main__.py \
     src/server/bos/utils.py \
     src/server/bos/dbclient.py \
     src/server/bos/specialized_encoder.py \
     lib/server/bos/

# Testing Image
FROM base as testing
WORKDIR /app/
COPY src/server/bos/test lib/server/bos/test/
COPY docker_test_entry.sh .
COPY test-requirements.txt .
RUN apk add --no-cache --repository http://car.dev.cray.com/artifactory/mirror-alpine/edge/testing etcd etcd-ctl
RUN pip3 install --no-cache-dir -r test-requirements.txt
CMD [ "./docker_test_entry.sh" ]

# Codestyle reporting
FROM testing as codestyle
WORKDIR /app/
COPY docker_codestyle_entry.sh setup.cfg ./
CMD [ "./docker_codestyle_entry.sh" ]

# API Testing image
FROM testing as api-testing
WORKDIR /app/
COPY docker_api_test_entry.sh run_apitests.py ./
COPY api_tests/ api_tests/
CMD [ "./docker_api_test_entry.sh" ]

# Debug Image
FROM base as debug
ENV PYTHONPATH "/app/lib/server"
WORKDIR /app/
EXPOSE 80
RUN apk add --no-cache uwsgi-python3 busybox-extras && \
    pip3 install rpdb
COPY config/uwsgi.ini ./
ENTRYPOINT ["uwsgi", "--ini", "/app/uwsgi.ini"]


# Application Image
FROM base as application
ENV PYTHONPATH "/app/lib/server"
WORKDIR /app/
EXPOSE 80
RUN apk add --no-cache uwsgi-python3 && \
    rm -rf /usr/lib/python3.8/site-packages/swagger_ui_bundle/vendor/swagger-ui-2.2.10
COPY config/uwsgi.ini ./
ENTRYPOINT ["uwsgi", "--ini", "/app/uwsgi.ini"]
