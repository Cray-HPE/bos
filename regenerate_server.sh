#!/bin/bash
# Copyright 2019-2020 Cray Inc.
docker run --rm -v ${PWD}:/local -e PYTHON_POST_PROCESS_FILE="/usr/local/bin/yapf -i" openapitools/openapi-generator-cli:v4.1.2 \
  generate \
    -i local/api/openapi.yaml \
    -g python-flask \
    -o local/src/server \
    -c local/config/autogen-server.json \
    --generate-alias-as-model

echo "Code has been generated within src/server for development purposes ONLY"
echo "This project is setup to automatically generate server side code as a"
echo "function of docker image build. Adjust .gitignore before checking in"
echo "anything you did not author!"

