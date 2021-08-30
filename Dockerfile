# Dockerfile for Cray Boot Orchestration Service (BOS)
# Copyright 2019-2021 Hewlett Packard Enterprise Development LP
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#
# (MIT License)

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
FROM artifactory.algol60.net/docker.io/alpine:3.12.4 as base
WORKDIR /app
COPY --from=codegen /app .
COPY constraints.txt requirements.txt ./
# Update packages to avoid security problems
RUN apk add --upgrade --no-cache apk-tools busybox && \
    apk add --no-cache gcc g++ python3-dev py3-pip musl-dev libffi-dev openssl-dev && \
    pip3 install --no-cache-dir -U pip && \
    pip3 install --no-cache-dir -r requirements.txt
COPY src/server/bos/controllers lib/server/bos/controllers
COPY src/server/bos/__main__.py \
     src/server/bos/utils.py \
     src/server/bos/dbclient.py \
     src/server/bos/specialized_encoder.py \
     lib/server/bos/

# Testing image
FROM base as testing
WORKDIR /app/
COPY src/server/bos/test lib/server/bos/test/
COPY docker_test_entry.sh .
COPY test-requirements.txt .
RUN apk add --no-cache --repository https://arti.dev.cray.com/artifactory/mirror-alpine/edge/testing/ etcd etcd-ctl
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

# Debug image
FROM base as debug
ENV PYTHONPATH "/app/lib/server"
WORKDIR /app/
EXPOSE 9000
RUN apk add --no-cache uwsgi-python3 busybox-extras && \
    pip3 install rpdb
COPY config/uwsgi.ini ./
ENTRYPOINT ["uwsgi", "--ini", "/app/uwsgi.ini"]


# Application image
FROM base as application
ENV PYTHONPATH "/app/lib/server"
WORKDIR /app/
EXPOSE 9000
RUN apk add --no-cache uwsgi-python3 && \
    rm -rf /usr/lib/python3.8/site-packages/swagger_ui_bundle/vendor/swagger-ui-2.2.10
COPY config/uwsgi.ini ./
USER 65534:65534
ENTRYPOINT ["uwsgi", "--ini", "/app/uwsgi.ini"]
