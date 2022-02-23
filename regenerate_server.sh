#!/usr/bin/env bash
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

CLI_VERSION="v5.3.0"
cp ./api/openapi.yaml.in ./api/openapi.yaml
docker run --rm -v ${PWD}:/local -e PYTHON_POST_PROCESS_FILE="/usr/local/bin/yapf -i" openapitools/openapi-generator-cli:${CLI_VERSION} \
  generate \
    -i api/openapi.yaml \
    -g python-flask \
    -o src/ \
    -c config/autogen-server.json \
    --generate-alias-as-model
rm ./api/openapi.yaml
echo "Code has been generated within src for development purposes ONLY."
echo "Code was generated using openapi-generator-cli version: $CLI_VERSION."
echo "This project is setup to automatically generate server-side code as a"
echo "function of Docker image build. Adjust .gitignore before checking in"
echo "anything you did not author!"

