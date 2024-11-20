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
ARG OPENAPI_IMAGE=artifactory.algol60.net/csm-docker/stable/docker.io/openapitools/openapi-generator-cli:v7.10.0
ARG ALPINE_BASE_IMAGE=artifactory.algol60.net/csm-docker/stable/docker.io/library/alpine:3

# Generate Code
FROM $OPENAPI_IMAGE AS codegen
WORKDIR /app
COPY api/openapi.yaml api/openapi.yaml
COPY config/autogen-server.json config/autogen-server.json
# Validate the spec file
RUN /usr/local/bin/docker-entrypoint.sh validate \
    -i api/openapi.yaml \
    --recommend
RUN ls /usr/local/bin/yapf && dpkg -S /usr/local/bin/yapf || true
RUN apt-file search yapf || true
ENV PYTHON_POST_PROCESS_FILE="/usr/local/bin/yapf -i"
RUN /usr/local/bin/docker-entrypoint.sh generate \
    -i api/openapi.yaml \
    -g python-flask \
    -o lib \
    -c config/autogen-server.json \
    --generate-alias-as-model \
    --enable-post-process-file
RUN /usr/local/bin/docker-entrypoint.sh help -g python-flask || true
RUN /usr/local/bin/docker-entrypoint.sh help -g python || true
RUN /usr/local/bin/docker-entrypoint.sh generate \
    -i api/openapi.yaml \
    -g python \
    -o lib2 \
    -c config/autogen-server.json \
    --generate-alias-as-model \
    --enable-post-process-file

# Start by taking a base Alpine image, copying in our generated code,
# applying some updates, and creating our virtual Python environment
FROM $ALPINE_BASE_IMAGE AS alpine-base
WORKDIR /app
# Copy in generated code
COPY --from=codegen /app/lib/ /app/lib
COPY --from=codegen /app/lib2/ /app/lib2
# Copy in Python constraints file
COPY constraints.txt /app/
# Update packages to avoid security problems
RUN --mount=type=secret,id=netrc,target=/root/.netrc \
    apk add --upgrade --no-cache apk-tools busybox && \
    apk update && \
    apk add --no-cache python3-dev py3-pip && \
    apk -U upgrade --no-cache
ENV VIRTUAL_ENV=/app/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
RUN --mount=type=secret,id=netrc,target=/root/.netrc \
    pip3 install --no-cache-dir -U pip -c constraints.txt && \
    pip3 list --format freeze


# Generate JSON version of openapi spec and then convert its
# schemas using our convert_oas utility
FROM alpine-base AS openapi-json-converter
WORKDIR /app
COPY api/openapi.yaml convert-oas-requirements.txt /app
RUN --mount=type=secret,id=netrc,target=/root/.netrc \
    apk add --no-cache yq && \
    apk -U upgrade --no-cache && \
    yq -o=json /app/openapi.yaml > /app/openapi.json && \
    pip3 install --no-cache-dir -r convert-oas-requirements.txt && \
    pip3 list --format freeze && \
    python3 -m convert_oas30_schemas /app/openapi.json /app/lib/bos/server/openapi.jsonschema && \
    cat /app/lib/bos/server/openapi.jsonschema
RUN pylint /app/convert_oas/convert_oas.py || true

# Base image
FROM alpine-base AS base
WORKDIR /app
# Move autogenerated server requirements aside so that they can be referenced by
# project-wide requirements.txt; this allows us to specify download source and
# additional required libraries necessary for developer authored controller/database
# code.
#
# The openapi-generator creates a requirements file that specifies exactly Flask==2.1.1
# However, using Flask 2.2.5 is also compatible, and resolves a CVE.
# Accordingly, we relax their requirements file.
RUN mv -v lib/requirements.txt lib/bos/server/requirements.txt && \
    cat lib/bos/server/requirements.txt && \
    sed -i 's/Flask == 2\(.*\)$/Flask >= 2\1\nFlask < 3/' lib/bos/server/requirements.txt && \
    cat lib/bos/server/requirements.txt
# Then copy all src into the base image
COPY src/bos/ /app/lib/bos/
# Copy jsonschema data file over from previous layer
COPY --from=openapi-json-converter /app/lib/bos/server/openapi.jsonschema /app/lib/bos/server/openapi.jsonschema
COPY requirements.txt /app/
# 1. Install and update packages to avoid security problems
# 2. Create a virtual environment in which we can install Python packages. This
#    isolates our installation from the system installation.
RUN --mount=type=secret,id=netrc,target=/root/.netrc \
    apk add --no-cache gcc g++ musl-dev libffi-dev openssl-dev && \
    apk -U upgrade --no-cache && \
    pip3 install --no-cache-dir -U pip -c constraints.txt && \
    pip3 list --format freeze && \
    pip3 install --no-cache-dir -r requirements.txt && \
    pip3 list --format freeze && \
    cd lib && \
    pip3 install --no-cache-dir . -c ../constraints.txt && \
    pip3 list --format freeze


# Base testing image
FROM base AS testing
WORKDIR /app
COPY test-requirements.txt .
RUN --mount=type=secret,id=netrc,target=/root/.netrc \
    cd /app && \
    pip3 install --no-cache-dir -r test-requirements.txt && \
    pip3 list --format freeze


# lint base
FROM base AS lint-base
COPY srclist.txt docker_pylint.sh /app/venv/


# Pylint reporting
FROM lint-base AS pylint-base
WORKDIR /app
RUN --mount=type=secret,id=netrc,target=/root/.netrc \
    pip3 install --no-cache-dir pylint -c constraints.txt && \
    pip3 list --format freeze


# Pylint errors-only
FROM pylint-base AS pylint-errors-only
WORKDIR /app/venv
CMD [ "./docker_pylint.sh", "--errors-only" ]


# Pylint full
FROM pylint-base AS pylint-full
WORKDIR /app/venv
CMD [ "./docker_pylint.sh", "--fail-under", "9" ]


# mypy
FROM lint-base AS mypy
WORKDIR /app/venv
COPY mypy-requirements.txt /app/
COPY mypy.ini /app/venv/
RUN --mount=type=secret,id=netrc,target=/root/.netrc \
    cd /app && \
    pip3 install --no-cache-dir -r mypy-requirements.txt && \
    pip3 list --format freeze
CMD [ "./docker_pylint.sh", "mypy" ]


# Codestyle reporting
FROM testing AS codestyle
WORKDIR /app
COPY docker_codestyle_entry.sh setup.cfg ./
CMD [ "./docker_codestyle_entry.sh" ]


# API Testing image
FROM testing AS api-testing
WORKDIR /app
COPY docker_api_test_entry.sh run_apitests.py ./
COPY api_tests/ api_tests/
CMD [ "./docker_api_test_entry.sh" ]


# Intermediate image
FROM base AS intermediate
WORKDIR /app
EXPOSE 9000
RUN apk add --no-cache uwsgi uwsgi-python3
COPY config/uwsgi.ini ./
ENTRYPOINT ["uwsgi", "--ini", "/app/uwsgi.ini"]


# Debug image
FROM intermediate AS debug
ENV PYTHONPATH "/app/lib/server"
WORKDIR /app
RUN apk add --no-cache busybox-extras && \
    apk -U upgrade --no-cache && \
    pip3 install --no-cache-dir rpdb -c constraints.txt && \
    pip3 list --format freeze


# Application image
FROM intermediate AS application
WORKDIR /app
USER 65534:65534
