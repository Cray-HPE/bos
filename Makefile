#
# MIT License
#
# (C) Copyright 2021-2023 Hewlett Packard Enterprise Development LP
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
RPM_VERSION ?= $(shell head -1 .version)
RPM_RELEASE ?= $(shell head -1 .rpm_release)
API_VERSION ?= $(shell head -1 .api_version)
CHART_VERSION ?= $(shell head -1 .chart_version)

HELM_UNITTEST_IMAGE ?= quintush/helm-unittest:3.3.0-0.2.5

ifneq ($(wildcard ${HOME}/.netrc),)
	DOCKER_ARGS ?= --secret id=netrc,src=${HOME}/.netrc
endif

# Common RPM variables
BUILD_METADATA ?= "1~development~$(shell git rev-parse --short HEAD)"

# We copy the built RPMs to these directories to simplify publishing them
RPM_IMAGE_DIR ?= dist/rpmbuild/RPMS/noarch
SRC_RPM_IMAGE_DIR ?= dist/rpmbuild/SRPMS

# bos-reporter RPM variables
RPTR_BUILD_DIR ?= $(PWD)/dist/bos-rptr-rpmbuild
RPTR_SPEC_NAME ?= bos-reporter
RPTR_SPEC_FILE ?= ${RPTR_SPEC_NAME}.spec
RPTR_SOURCE_NAME ?= ${RPTR_SPEC_NAME}-${RPM_VERSION}-${RPM_RELEASE}
RPTR_SOURCE_PATH := ${RPTR_BUILD_DIR}/SOURCES/${RPTR_SOURCE_NAME}.tar.bz2

all : runbuildprep lint image chart rptr_rpm
local: cms_meta_tools runbuildprep image chart_setup chart_package
chart: chart_setup chart_package chart_test
rptr_rpm: rptr_rpm_package_source rptr_rpm_build_source rptr_rpm_build

clone_input_files:
		cp ${CHART_PATH}/${NAME}/Chart.yaml.in ${CHART_PATH}/${NAME}/Chart.yaml
		cp ${CHART_PATH}/${NAME}/values.yaml.in ${CHART_PATH}/${NAME}/values.yaml
		cp bos-reporter.spec.in bos-reporter.spec
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

rpm_prepare:
		mkdir -p $(RPM_IMAGE_DIR) \
				 $(SRC_RPM_IMAGE_DIR)
rptr_rpm_prepare:
		rm -rf $(RPTR_BUILD_DIR)
		mkdir -p $(RPTR_BUILD_DIR)/SPECS \
				 $(RPTR_BUILD_DIR)/SOURCES
		cp $(RPTR_SPEC_FILE) $(RPTR_BUILD_DIR)/SPECS/
		cat $(RPTR_SPEC_FILE) $(RPTR_BUILD_DIR)/SPECS/bos-reporter.spec

image:
		docker build --pull ${DOCKER_ARGS} --tag '${NAME}:${DOCKER_VERSION}' .

chart_package:
		helm dep up ${CHART_PATH}/${NAME}
		helm package ${CHART_PATH}/${NAME} -d ${CHART_PATH}/.packaged --app-version ${DOCKER_VERSION} --version ${CHART_VERSION}

chart_test:
		helm lint "${CHART_PATH}/${NAME}"
		docker run --rm -v ${PWD}/${CHART_PATH}:/apps ${HELM_UNITTEST_IMAGE} -3 ${NAME}

rptr_rpm_package_source:
		tar --transform 'flags=r;s,^,/$(RPTR_SOURCE_NAME)/,' -cvjf $(RPTR_SOURCE_PATH) \
			./${RPTR_SPEC_FILE} \
			./src \
			./LICENSE

rptr_rpm_build_source:
		BUILD_METADATA=$(BUILD_METADATA) rpmbuild -ts $(RPTR_SOURCE_PATH) --define "_topdir $(RPTR_BUILD_DIR)"
		cp $(RPTR_BUILD_DIR)/SRPMS/*.rpm $(SRC_RPM_IMAGE_DIR)

rptr_rpm_build:
		BUILD_METADATA=$(BUILD_METADATA) rpmbuild -ba $(RPTR_SPEC_FILE) --define "_topdir $(RPTR_BUILD_DIR)"
		cp $(RPTR_BUILD_DIR)/RPMS/noarch/*.rpm $(RPM_IMAGE_DIR)

rpm_build_clean:
		rm -rf $(RPM_IMAGE_DIR)/*

rpm_build_source_clean:
		rm -rf $(SRC_RPM_IMAGE_DIR)/*
