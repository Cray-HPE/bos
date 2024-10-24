#
# MIT License
#
# (C) Copyright 2021-2024 Hewlett Packard Enterprise Development LP
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
# If you wish to perform a local build, you will need to clone or copy the contents of the
# cms-meta-tools repo to ./cms_meta_tools

NAME ?= cray-bos
CHART_PATH ?= kubernetes
DOCKER_VERSION ?= $(shell head -1 .docker_version)
API_VERSION ?= $(shell head -1 .api_version)
CHART_VERSION ?= $(shell head -1 .chart_version)

HELM_UNITTEST_IMAGE ?= quintush/helm-unittest:3.3.0-0.2.5

ifneq ($(wildcard ${HOME}/.netrc),)
	DOCKER_ARGS ?= --secret id=netrc,src=${HOME}/.netrc
endif

all : runbuildprep lint image chart
local: cms_meta_tools runbuildprep image chart_setup chart_package
chart: chart_setup chart_package chart_test
image: image_setup image_build image_build_pylint_errors image_run_pylint_errors image_build_pylint_full image_run_pylint_full

clone_input_files:
		cp ${CHART_PATH}/${NAME}/Chart.yaml.in ${CHART_PATH}/${NAME}/Chart.yaml
		cp ${CHART_PATH}/${NAME}/values.yaml.in ${CHART_PATH}/${NAME}/values.yaml
		cp constraints.txt.in constraints.txt
		cp src/setup.py.in src/setup.py
		cp api/openapi.yaml.in api/openapi.yaml

cms_meta_tools:
		rm -rf cms-meta-tools
		git clone --depth 1 --no-single-branch git@github.com:Cray-HPE/cms-meta-tools.git ./cms_meta_tools

runbuildprep:   clone_input_files
		grep "^[0-9][0-9]*[.][0-9][[0-9]*[.][0-9][0-9]*" .version > openapi.version
		./cms_meta_tools/scripts/runBuildPrep.sh
		mkdir -p ${CHART_PATH}/.packaged

chart_setup:
		printf "\nglobal:\n  appVersion: ${DOCKER_VERSION}" >> ${CHART_PATH}/${NAME}/values.yaml

lint:
		./cms_meta_tools/scripts/runLint.sh

image_setup:
		# Create list of BOS Python source files, to be checked later by pylint
		find src/bos -type f -name \*.py -print | sed 's#^src/#/app/lib/#' | tr '\n' ' ' | tee srclist.txt

image_build:
		docker build --pull ${DOCKER_ARGS} --tag '${NAME}:${DOCKER_VERSION}' .

image_build_pylint_errors:
		docker build --pull ${DOCKER_ARGS} --target pylint-errors-only --tag 'pylint-errors-only:${DOCKER_VERSION}' .

image_run_pylint_errors:
		docker run --rm 'pylint-errors-only:${DOCKER_VERSION}'

image_build_pylint_full:
		docker build --pull ${DOCKER_ARGS} --target pylint-full --tag 'pylint-full:${DOCKER_VERSION}' .

image_run_pylint_full:
		docker run --rm 'pylint-full:${DOCKER_VERSION}'

chart_package:
		helm dep up ${CHART_PATH}/${NAME}
		helm package ${CHART_PATH}/${NAME} -d ${CHART_PATH}/.packaged --app-version ${DOCKER_VERSION} --version ${CHART_VERSION}

chart_test:
		helm lint "${CHART_PATH}/${NAME}"
		docker run --rm -v ${PWD}/${CHART_PATH}:/apps ${HELM_UNITTEST_IMAGE} -3 ${NAME}
