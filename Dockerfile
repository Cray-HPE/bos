# Dockerfile for Cray Boot Orchestration Service (BOS)
# Copyright 2019-2020 Cray Inc.

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
FROM dtr.dev.cray.com/baseos/alpine:3.11.5 as base
WORKDIR /app
COPY --from=codegen /app .
COPY constraints.txt requirements.txt ./
RUN apk add --no-cache gcc g++ python3-dev musl-dev libffi-dev openssl-dev && \
    PIP_INDEX_URL=http://dst.us.cray.com/dstpiprepo/simple \
    PIP_TRUSTED_HOST=dst.us.cray.com \
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
# Once CASMCMS-5334 is fixed, the reference to the external repository can be removed.
RUN apk add --no-cache --repository http://dl-3.alpinelinux.org/alpine/edge/testing etcd etcd-ctl
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
RUN apk add --no-cache uwsgi-python3
COPY config/uwsgi.ini ./
ENTRYPOINT ["uwsgi", "--ini", "/app/uwsgi.ini"]
