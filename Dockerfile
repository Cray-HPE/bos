#
# MIT License
#
# (C) Copyright 2019-2024 Hewlett Packard Enterprise Development LP
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
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#
# Dockerfile for Cray Boot Orchestration Service (BOS)

# Upstream Build Args
ARG OPENAPI_IMAGE=artifactory.algol60.net/csm-docker/stable/docker.io/openapitools/openapi-generator-cli:v7.5.0
ARG ALPINE_BASE_IMAGE=artifactory.algol60.net/csm-docker/stable/docker.io/library/alpine:3

# Generate Code
FROM $OPENAPI_IMAGE as codegen
WORKDIR /app
COPY api/openapi.yaml api/openapi.yaml
COPY config/autogen-server.json config/autogen-server.json
ENV JAVA_OPTS="${JAVA_OPTS}  -Dlog.level=debug"
RUN /usr/local/bin/docker-entrypoint.sh validate \
    -i api/openapi.yaml \
    --recommend
RUN /usr/local/bin/docker-entrypoint.sh generate \
    -i api/openapi.yaml \
    -g python-flask \
    -o lib \
    -c config/autogen-server.json \
    -v \
    --generate-alias-as-model

# Base image
FROM $ALPINE_BASE_IMAGE as base
WORKDIR /app
# We apply all generated code first
COPY --from=codegen /app/lib/ /app/lib
# Move autogenerated server requirements aside so that they can be referenced by
# project-wide requirements.txt; this allows us to specify download source and
# additional required libraries necessary for developer authored controller/database
# code.
RUN mv lib/requirements.txt lib/bos/server/requirements.txt
# Then copy all src into the base image
COPY src/bos/ /app/lib/bos/
COPY constraints.txt requirements.txt /app/
# Update packages to avoid security problems
RUN apk add --upgrade --no-cache apk-tools busybox && \
    apk update && \
    apk add --no-cache gcc g++ python3-dev py3-pip musl-dev libffi-dev openssl-dev && \
    apk -U upgrade --no-cache
# Create a virtual environment in which we can install Python packages. This
# isolates our installation from the system installation.
ENV VIRTUAL_ENV=/app/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
RUN pip3 install --no-cache-dir -U pip -c constraints.txt
RUN --mount=type=secret,id=netrc,target=/root/.netrc pip3 install --no-cache-dir -r requirements.txt
RUN cd lib && pip3 install --no-cache-dir . -c ../constraints.txt

# Base testing image
FROM base as testing
WORKDIR /app
COPY test-requirements.txt .
RUN --mount=type=secret,id=netrc,target=/root/.netrc cd /app && pip3 install --no-cache-dir -r test-requirements.txt

# Codestyle reporting
FROM testing as codestyle
WORKDIR /app
COPY docker_codestyle_entry.sh setup.cfg ./
CMD [ "./docker_codestyle_entry.sh" ]

# API Testing image
FROM testing as api-testing
WORKDIR /app
COPY docker_api_test_entry.sh run_apitests.py ./
COPY api_tests/ api_tests/
CMD [ "./docker_api_test_entry.sh" ]

# Intermediate image
FROM base as intermediate
WORKDIR /app
EXPOSE 9000
RUN apk add --no-cache uwsgi uwsgi-python3
COPY config/uwsgi.ini ./
ENTRYPOINT ["uwsgi", "--ini", "/app/uwsgi.ini"]

# Debug image
FROM intermediate as debug
ENV PYTHONPATH "/app/lib/server"
WORKDIR /app
RUN apk add --no-cache busybox-extras && \
    pip3 install --no-cache-dir rpdb -c constraints.txt

# Application image
FROM intermediate as application
WORKDIR /app
USER 65534:65534

